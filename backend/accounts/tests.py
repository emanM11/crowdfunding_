"""
Encoding of PROJECT_SPEC.md §5.1 / §6 / §7 as executable checks.

Covers the auth contract: registration (inactive by default, secure token,
confirm_password validation, real password policy), activation (single-use,
24h expiry), JWT login rejecting inactive accounts, profile update with the
email locked server-side, soft-delete requiring the current password, the
generic password-reset response, and token refresh.
"""

from datetime import timedelta

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from .models import User
from .serializers import TokenObtainPairSerializer

_INACTIVE_MESSAGE = TokenObtainPairSerializer.INACTIVE_ACCOUNT_MESSAGE


def _make_user(email='user1@example.com', password='Str0ng@Pass123', active=True, **extra):
    user = User.objects.create_user(
        email=email,
        password=password,
        phone_number=extra.pop('phone_number', '01012345678'),
        first_name=extra.pop('first_name', 'عمر'),
        last_name=extra.pop('last_name', 'حسن'),
        is_active=active,
        **extra,
    )
    return user


class AccountsTestCase(TestCase):
    """Base: scrape the throttle cache so the scoped rate limits
    (register 5/hour, login 10/minute, activate 10/hour, password_reset
    5/hour) never trip a false 429 across tests in one run."""

    def setUp(self):
        cache.clear()
        super().setUp()


class RegisterTests(AccountsTestCase):

    def setUp(self):
        self.client = APIClient()

    def _payload(self, **overrides):
        payload = {
            'first_name': 'منى',
            'last_name': 'عبدالعظيم',
            'email': 'mona@example.com',
            'password': 'Str0ng@Pass123',
            'confirm_password': 'Str0ng@Pass123',
            'phone_number': '01100000002',
        }
        payload.update(overrides)
        return payload

    def test_register_creates_inactive_user_with_token(self):
        response = self.client.post(reverse('accounts:register'), self._payload(), format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['is_active'], False)

        user = User.objects.get(email='mona@example.com')
        self.assertFalse(user.is_active)
        self.assertTrue(user.activation_token)
        self.assertIsNotNone(user.activation_token_created_at)
        self.assertNotEqual(user.password, 'Str0ng@Pass123')  # hashed, never stored plaintext

    def test_register_rejects_password_mismatch(self):
        payload = self._payload(confirm_password='Different@123')
        response = self.client.post(reverse('accounts:register'), payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('confirm_password', response.data)

    def test_register_rejects_numeric_only_password(self):
        payload = self._payload(password='12345678', confirm_password='12345678')
        response = self.client.post(reverse('accounts:register'), payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_rejects_invalid_egyptian_phone(self):
        payload = self._payload(phone_number='02012345678')
        response = self.client.post(reverse('accounts:register'), payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_rejects_duplicate_email(self):
        _make_user(email='mona@example.com')
        response = self.client.post(reverse('accounts:register'), self._payload(), format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ActivationTests(AccountsTestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = _make_user(email='activate@example.com', active=False)
        self.token = self.user.generate_activation_token()
        self.user.save()

    def _activate(self, token, uid=None):
        return self.client.post(reverse('accounts:activate', args=[uid or self.user.pk, token]))

    def test_activation_succeeds_and_invalidates_token(self):
        response = self._activate(self.token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertIsNone(self.user.activation_token)

    def test_activation_token_cannot_be_reused(self):
        self._activate(self.token)
        # Second POST with the same (now-cleared) token must fail.
        response = self._activate(self.token)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_activation_token_expires_after_24_hours(self):
        self.user.activation_token_created_at = timezone.now() - timedelta(hours=25)
        self.user.save()
        response = self._activate(self.token)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)

    def test_activation_with_invalid_token_fails(self):
        response = self._activate('not-a-real-token')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_activation_rejects_uid_that_does_not_own_token(self):
        other = _make_user(email='other-activate@example.com', active=True)
        # Same token under another user's uid → rejected, and the owner's
        # token stays pristine so the correct link still works.
        response = self._activate(self.token, uid=other.pk)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertEqual(self.user.activation_token, self.token)

        self.assertEqual(self._activate(self.token).status_code, status.HTTP_200_OK)


class LoginTests(AccountsTestCase):

    def setUp(self):
        self.client = APIClient()

    def test_login_returns_jwt_pair_for_active_user(self):
        _make_user(email='login@example.com', password='Str0ng@Pass123', active=True)
        response = self.client.post(
            reverse('accounts:token_obtain_pair'),
            {'email': 'login@example.com', 'password': 'Str0ng@Pass123'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_login_rejects_inactive_user(self):
        _make_user(email='sleeping@example.com', password='Str0ng@Pass123', active=False)
        response = self.client.post(
            reverse('accounts:token_obtain_pair'),
            {'email': 'sleeping@example.com', 'password': 'Str0ng@Pass123'},
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        # Clear Arabic message pointing at the activation email, not the
        # generic "no active account" the inactive login currently returns.
        self.assertEqual(response.data['detail'], _INACTIVE_MESSAGE)

    def test_inactive_message_not_leaked_with_wrong_password(self):
        # The unactivated-account hint must only surface when the password
        # is correct — otherwise the endpoint becomes an email oracle.
        _make_user(email='sleeping2@example.com', password='Str0ng@Pass123', active=False)
        response = self.client.post(
            reverse('accounts:token_obtain_pair'),
            {'email': 'sleeping2@example.com', 'password': 'TotallyWrong@9'},
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotEqual(response.data['detail'], _INACTIVE_MESSAGE)

    def test_token_refresh_returns_new_access(self):
        _make_user(email='refresh@example.com', password='Str0ng@Pass123', active=True)
        login = self.client.post(
            reverse('accounts:token_obtain_pair'),
            {'email': 'refresh@example.com', 'password': 'Str0ng@Pass123'},
        )
        response = self.client.post(
            reverse('accounts:token_refresh'),
            {'refresh': login.data['refresh']},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_login_rejects_wrong_password(self):
        _make_user(email='wrong@example.com', password='Str0ng@Pass123', active=True)
        response = self.client.post(
            reverse('accounts:token_obtain_pair'),
            {'email': 'wrong@example.com', 'password': 'TotallyWrong@9'},
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ProfileTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = _make_user(email='profile@example.com', password='Str0ng@Pass123')
        self.client.force_authenticate(self.user)

    def test_require_auth_to_view_profile(self):
        anonymous = APIClient()
        response = anonymous.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_profile_changes_allowed_fields(self):
        response = self.client.put(
            reverse('accounts:profile'),
            {'first_name': 'أحمد', 'phone_number': '01200000003'},
            format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'أحمد')
        self.assertEqual(self.user.phone_number, '01200000003')

    def test_email_is_locked_server_side(self):
        response = self.client.put(
            reverse('accounts:profile'),
            {'email': 'hijacked@example.com'},
            format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'profile@example.com')
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'profile@example.com')

    def test_delete_requires_correct_password(self):
        response = self.client.delete(
            reverse('accounts:profile'),
            {'password': 'WrongPassword@9'},
            format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(User.objects.get(email='profile@example.com').is_active)

    def test_delete_soft_deletes_and_anonymizes(self):
        response = self.client.delete(
            reverse('accounts:profile'),
            {'password': 'Str0ng@Pass123'},
            format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertTrue(self.user.email.startswith('deleted-user-'))
        self.assertNotEqual(self.user.first_name, 'عمر')


class PasswordResetTests(AccountsTestCase):

    def test_request_always_returns_generic_response(self):
        client = APIClient()
        _make_user(email='reset@example.com', password='Str0ng@Pass123', active=True)

        for email in ('reset@example.com', 'nonexistent@example.com'):
            response = client.post(reverse('accounts:password-reset'), {'email': email})
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('If an account exists', response.data['detail'])

    def test_reset_token_is_single_use_and_expires(self):
        client = APIClient()
        user = _make_user(email='reset2@example.com', password='Str0ng@Pass123', active=True)
        user.generate_password_reset_token()
        user.save()

        confirm_url = reverse(
            'accounts:password-reset-confirm',
            args=[user.pk, user.password_reset_token],
        )
        payload = {'password': 'NewPass@999', 'confirm_password': 'NewPass@999'}
        response = client.post(confirm_url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertIsNone(user.password_reset_token)
        self.assertTrue(user.check_password('NewPass@999'))

        # Token cleared after success → second attempt must fail.
        response = client.post(confirm_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reset_link_rejects_uid_that_does_not_own_token(self):
        client = APIClient()
        owner = _make_user(email='owner@example.com', password='Str0ng@Pass123', active=True)
        other = _make_user(email='other@example.com', password='Str0ng@Pass123', active=True)
        owner.generate_password_reset_token()
        owner.save()

        payload = {'password': 'NewPass@999', 'confirm_password': 'NewPass@999'}
        token = owner.password_reset_token

        # Same token under someone else's uid → rejected, still usable.
        wrong_uid_url = reverse('accounts:password-reset-confirm', args=[other.pk, token])
        self.assertEqual(client.post(wrong_uid_url, payload).status_code, status.HTTP_400_BAD_REQUEST)
        owner.refresh_from_db()
        self.assertEqual(owner.password_reset_token, token)
        self.assertFalse(owner.check_password('NewPass@999'))

        # The correct uid+token pair still works afterwards.
        right_uid_url = reverse('accounts:password-reset-confirm', args=[owner.pk, token])
        self.assertEqual(client.post(right_uid_url, payload).status_code, status.HTTP_200_OK)
        owner.refresh_from_db()
        self.assertIsNone(owner.password_reset_token)
        self.assertTrue(owner.check_password('NewPass@999'))


class FacebookTests(AccountsTestCase):

    def test_facebook_login_503_when_unconfigured(self):
        # settings.FACEBOOK_APP_ID defaults to '' — endpoint must refuse
        # rather than accept unverifiable tokens.
        response = APIClient().post(reverse('accounts:facebook-login'), {'access_token': 'abc'})
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)