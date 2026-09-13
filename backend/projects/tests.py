"""
Encoding of PROJECT_SPEC.md §5.4–5.6 / §6 / §8 for projects as executable
checks: create/list/detail, the strict <25% cancellation rule, the donation
rules (auth, not-own-project, inside date window, amount > 0), creator-only
updates/rewards, and my-projects / my-donations scoping.
"""

from datetime import timedelta
from io import BytesIO
from types import SimpleNamespace

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from rest_framework import status
from rest_framework.test import APIClient
from unittest.mock import patch

from accounts.models import User
from .models import Category, Donation, Project, ProjectUpdate, RewardTier, Tag
from .payments import TEST_CARD_DECLINED, TEST_CARD_SUCCESS, GatewayError


def _make_user(email='u1@example.com', password='Str0ng@Pass123', **extra):
    return User.objects.create_user(
        email=email,
        password=password,
        phone_number=extra.pop('phone_number', '01012345678'),
        first_name=extra.pop('first_name', 'محمود'),
        last_name=extra.pop('last_name', 'سعيد'),
        is_active=True,
        **extra,
    )


def _jpeg(name='p.jpg'):
    buffer = BytesIO()
    Image.new('RGB', (2, 2), 'red').save(buffer, 'JPEG')
    return buffer.getvalue()


def _today():
    return timezone.localdate()


def _future_expiry():
    """A valid, non-expired MM/YY two years out."""
    now = timezone.now()
    return f'12/{((now.year + 2) % 100):02d}'


def _card_payload(**overrides):
    """A well-formed donation payment request (Stripe-style adopt test card)."""
    payload = {
        'amount': '120.50',
        'currency': 'EGP',
        'cardholder_name': 'Mahmoud Said',
        'card_number': TEST_CARD_SUCCESS,
        'card_expiry': _future_expiry(),
        'card_cvc': '123',
    }
    payload.update(overrides)
    return payload


class ProjectTestCase(TestCase):

    def setUp(self):
        self.category = Category.objects.create(name='تعليم')
        self.creator = _make_user(email='creator@example.com')
        self.backer = _make_user(email='backer@example.com')
        self.client = APIClient()

    def create_project(self, creator=None, target=400, start=None, end=None, **extra):
        project = Project.objects.create(
            title=extra.pop('title', 'مشروع تجريبي'),
            details=extra.pop('details', 'تفاصيل المشروع'),
            category=self.category,
            creator=creator or self.creator,
            total_target=target,
            start_date=start or (_today() - timedelta(days=1)),
            end_date=end or (_today() + timedelta(days=30)),
            **extra,
        )
        return project


class ProjectListCreateTests(ProjectTestCase):

    def test_anon_cannot_create_project(self):
        response = self.client.post(reverse('projects:project-list-create'), {'title': 'x'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_creator_can_create_project_with_tags(self):
        self.client.force_authenticate(self.creator)
        response = self.client.post(
            reverse('projects:project-list-create'),
            {
                'title': 'مدرسة تعليمية',
                'details': 'بناء مدرسة جديدة',
                'category': self.category.id,
                'total_target': '50000.00',
                'start_date': (_today() - timedelta(days=1)).isoformat(),
                'end_date': (_today() + timedelta(days=60)).isoformat(),
                'tags': ['تعليم', 'بنية تحتية'],
            },
            format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = Project.objects.get(pk=response.data['id'])
        self.assertEqual(created.total_donations(), 0)
        self.assertEqual(set(created.tags.values_list('name', flat=True)), {'تعليم', 'بنية تحتية'})
        self.assertEqual(Tag.objects.count(), 2)

    def test_creator_can_upload_project_image(self):
        self.client.force_authenticate(self.creator)
        response = self.client.post(
            reverse('projects:project-list-create'),
            {
                'title': 'مشروع بصور',
                'details': 'تفاصيل',
                'category': self.category.id,
                'total_target': '1000.00',
                'start_date': (_today() - timedelta(days=1)).isoformat(),
                'end_date': (_today() + timedelta(days=30)).isoformat(),
                'images': [SimpleUploadedFile('p.jpg', _jpeg(), content_type='image/jpeg')],
            },
            format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = Project.objects.get(pk=response.data['id'])
        self.assertEqual(created.images.count(), 1)

    def test_list_is_paginated_and_contains_project(self):
        self.create_project(title='مشروع في القائمة')
        response = self.client.get(reverse('projects:project-list-create'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [item['title'] for item in response.data['results']]
        self.assertIn('مشروع في القائمة', titles)


class ProjectDetailTests(ProjectTestCase):

    def test_status_running_inside_window(self):
        project = self.create_project()
        response = self.client.get(reverse('projects:project-detail', args=[project.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'running')

    def test_status_ended_after_end_date(self):
        project = self.create_project(end=_today() - timedelta(days=1))
        response = self.client.get(reverse('projects:project-detail', args=[project.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'ended')

    def test_non_creator_cannot_update_project(self):
        project = self.create_project()
        self.client.force_authenticate(self.backer)
        response = self.client.put(
            reverse('projects:project-detail', args=[project.id]),
            {'title': 'استيلاء'},
            format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_creator_can_update_own_project(self):
        project = self.create_project()
        self.client.force_authenticate(self.creator)
        response = self.client.put(
            reverse('projects:project-detail', args=[project.id]),
            {
                'title': 'تم تعديله',
                'details': 'تفاصيل المشروع',
                'category': self.category.id,
                'total_target': '400.00',
                'start_date': (_today() - timedelta(days=1)).isoformat(),
                'end_date': (_today() + timedelta(days=30)).isoformat(),
            },
            format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        project.refresh_from_db()
        self.assertEqual(project.title, 'تم تعديله')


class ProjectCancelTests(ProjectTestCase):

    def test_cancel_succeeds_with_no_donations(self):
        project = self.create_project(target=400)
        self.client.force_authenticate(self.creator)
        response = self.client.post(reverse('projects:project-cancel', args=[project.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        project.refresh_from_db()
        self.assertEqual(project.computed_status, 'cancelled')

    def test_cancel_rejected_at_exactly_25_percent(self):
        project = self.create_project(target=400)
        Donation.objects.create(
            user=self.backer, project=project, amount='100.00',
            status=Donation.STATUS_SUCCESSFUL,
        )
        self.client.force_authenticate(self.creator)
        response = self.client.post(reverse('projects:project-cancel', args=[project.id]))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        project.refresh_from_db()
        self.assertNotEqual(project.computed_status, 'cancelled')

    def test_cancel_rejected_above_25_percent(self):
        project = self.create_project(target=400)
        Donation.objects.create(
            user=self.backer, project=project, amount='150.00',
            status=Donation.STATUS_SUCCESSFUL,
        )
        self.client.force_authenticate(self.creator)
        response = self.client.post(reverse('projects:project-cancel', args=[project.id]))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_only_creator_can_cancel(self):
        project = self.create_project(target=400)
        self.client.force_authenticate(self.backer)
        response = self.client.post(reverse('projects:project-cancel', args=[project.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_already_cancelled_cannot_be_cancelled_again(self):
        project = self.create_project(target=400)
        self.client.force_authenticate(self.creator)
        self.client.post(reverse('projects:project-cancel', args=[project.id]))
        response = self.client.post(reverse('projects:project-cancel', args=[project.id]))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class DonateTests(ProjectTestCase):
    """Gateway-backed donation flow (PROJECT_SPEC.md 5.6 + payment upgrade):
    the mock gateway accepts valid Luhn cards and declines the documented
    test-decline card; only confirmed charges raise current_fund."""

    def _post(self, project, payload):
        return self.client.post(reverse('projects:project-donate', args=[project.id]), payload)

    def _post_process(self, project, payload):
        return self.client.post(reverse('projects:project-donate-process', args=[project.id]), payload)

    def test_anon_cannot_donate(self):
        project = self.create_project()
        response = self._post(project, _card_payload())
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_creator_cannot_donate_to_own_project(self):
        project = self.create_project()
        self.client.force_authenticate(self.creator)
        response = self._post(project, _card_payload())
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_donate_rejected_when_project_ended(self):
        project = self.create_project(end=_today() - timedelta(days=1))
        self.client.force_authenticate(self.backer)
        response = self._post(project, _card_payload())
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_donate_rejected_when_project_cancelled(self):
        project = self.create_project(target=400, status='cancelled')
        self.client.force_authenticate(self.backer)
        response = self._post(project, _card_payload())
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_donate_rejected_before_start_date(self):
        project = self.create_project(start=_today() + timedelta(days=1))
        self.client.force_authenticate(self.backer)
        response = self._post(project, _card_payload())
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_donate_rejected_when_amount_zero_or_negative(self):
        project = self.create_project()
        self.client.force_authenticate(self.backer)
        for amount in ('0', '-10'):
            response = self._post(project, _card_payload(amount=amount))
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=amount)

    def test_invalid_card_rejected_with_field_errors(self):
        project = self.create_project()
        self.client.force_authenticate(self.backer)

        # Non-Luhn number.
        response = self._post(project, _card_payload(card_number='1111111111111111'))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('card_number', response.data)

        # Malformed expiry.
        response = self._post(project, _card_payload(card_expiry='13/30'))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('card_expiry', response.data)

        # Expired expiry.
        now = timezone.now()
        expired_month = f'{(now.month - 1) or 12:02d}'
        response = self._post(project, _card_payload(card_expiry=f'{expired_month}/99'))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('card_expiry', response.data)

        # Bad CVC length.
        response = self._post(project, _card_payload(card_cvc='12'))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('card_cvc', response.data)

        # Blank cardholder name.
        response = self._post(project, _card_payload(cardholder_name='   '))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('cardholder_name', response.data)

    def test_valid_donation_paid_and_marked_successful(self):
        project = self.create_project()
        self.client.force_authenticate(self.backer)
        response = self._post_process(project, _card_payload(amount='120.50'))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        donation = Donation.objects.get()
        self.assertEqual(donation.amount, __import__('decimal').Decimal('120.50'))
        self.assertEqual(donation.status, Donation.STATUS_SUCCESSFUL)
        self.assertEqual(donation.currency, 'EGP')
        self.assertEqual(donation.card_last4, '4242')
        self.assertRegex(donation.transaction_id, r'^MOCK-')
        self.assertFalse(donation.is_anonymous)

        project.refresh_from_db()
        self.assertEqual(project.current_fund, __import__('decimal').Decimal('120.50'))
        self.assertEqual(project.total_donations(), __import__('decimal').Decimal('120.50'))
        self.assertIn('transaction_id', response.data)
        self.assertEqual(response.data['status'], 'successful')
        self.assertEqual(response.data['payment_method'], '4242')

    def test_anonymous_flag_stored(self):
        project = self.create_project()
        self.client.force_authenticate(self.backer)
        response = self._post(project, _card_payload(amount='25.00', is_anonymous=True))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Donation.objects.get().is_anonymous)
        self.assertIs(response.data['is_anonymous'], True)

    def test_declined_card_marks_failed_and_does_not_raise_fund(self):
        project = self.create_project()
        self.client.force_authenticate(self.backer)
        response = self._post(project, _card_payload(card_number=TEST_CARD_DECLINED))
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(response.data['error_code'], 'card_declined')

        donation = Donation.objects.get()
        self.assertEqual(donation.status, Donation.STATUS_FAILED)
        self.assertIsNone(donation.transaction_id)

        project.refresh_from_db()
        self.assertEqual(project.current_fund, 0)
        self.assertEqual(project.total_donations(), 0)

    def test_declined_campaign_still_cancellable(self):
        project = self.create_project(target=400)
        self.client.force_authenticate(self.backer)
        self._post(project, _card_payload(amount='100.00', card_number=TEST_CARD_DECLINED))
        self.client.force_authenticate(self.creator)
        response = self.client.post(reverse('projects:project-cancel', args=[project.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_pending_failed_donations_never_count_toward_fund(self):
        project = self.create_project(target=400)
        Donation.objects.create(user=self.backer, project=project, amount='50.00')
        Donation.objects.create(
            user=self.backer, project=project, amount='30.00',
            status=Donation.STATUS_FAILED,
        )
        Donation.objects.create(
            user=self.backer, project=project, amount='20.00',
            status=Donation.STATUS_SUCCESSFUL,
        )
        self.assertEqual(project.total_donations(), __import__('decimal').Decimal('20.00'))
        self.assertTrue(project.can_be_cancelled())  # 20 < 100 (25% of 400)

    def test_idempotency_key_reuses_existing_donation(self):
        project = self.create_project()
        self.client.force_authenticate(self.backer)
        payload = _card_payload(amount='50.00', idempotency_key='same-key')
        first = self._post(project, payload)
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        second = self._post(project, payload)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(Donation.objects.count(), 1)
        project.refresh_from_db()
        self.assertEqual(project.current_fund, __import__('decimal').Decimal('50.00'))


class PaymentApiTests(ProjectTestCase):
    """PaymentIntents flow endpoints (config / confirm / webhook) with the
    Stripe API mocked — no network, but the full server-side verification
    + idempotent commit logic is exercised."""

    def _pending_donation(self, project, amount='120.50'):
        return Donation.objects.create(
            user=self.backer, project=project, amount=amount,
            status=Donation.STATUS_PENDING, gateway='stripe',
        )

    def _fake_intent(self, donation, *, status='succeeded', amount=None, currency='egp',
                     last_error=None, payment_method_details=None, user_id=None):
        return SimpleNamespace(
            id='pi_test_123',
            status=status,
            metadata={'donation_id': str(donation.id), 'user_id': str(user_id or donation.user_id)},
            amount=amount if amount is not None else 12050,
            currency=currency,
            last_payment_error=last_error,
            payment_method_details=payment_method_details or {'card': {'brand': 'visa', 'last4': '4242'}},
        )

    def test_payment_config_returns_mock_when_not_configured(self):
        response = self.client.get(reverse('projects:payment-config'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['gateway'], 'mock')

    def test_confirm_and_webhook_off_when_stripe_not_configured(self):
        project = self.create_project()
        donation = self._pending_donation(project)
        self.client.force_authenticate(self.backer)
        confirm = self.client.post(
            reverse('projects:project-donate-confirm', args=[project.id]),
            {'payment_intent_id': 'pi_1'},
        )
        self.assertEqual(confirm.status_code, status.HTTP_400_BAD_REQUEST)
        webhook = self.client.post(
            reverse('projects:payment-webhook'),
            data=b'{}',
            content_type='application/json',
        )
        self.assertEqual(webhook.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Donation.objects.count(), 1)  # nothing was forced

    def test_process_stripe_mode_returns_client_secret_without_card_fields(self):
        project = self.create_project()
        self.client.force_authenticate(self.backer)
        with (
            patch('projects.views.is_stripe_configured', return_value=True),
            patch('projects.views.create_payment_intent', return_value=('secret_test', 'pi_created')),
        ):
            response = self.client.post(
                reverse('projects:project-donate-process', args=[project.id]),
                {'amount': '120.50', 'currency': 'EGP', 'idempotency_key': 'k-1'},
            )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['gateway'], 'stripe')
        self.assertEqual(response.data['payment_intent_id'], 'pi_created')
        self.assertEqual(response.data['client_secret'], 'secret_test')
        donation = Donation.objects.get()
        self.assertEqual(donation.status, Donation.STATUS_PENDING)
        project.refresh_from_db()
        self.assertEqual(project.current_fund, 0)  # not raised until confirmed

    def test_confirm_success_commits_donation_and_fund(self):
        project = self.create_project()
        donation = self._pending_donation(project)
        self.client.force_authenticate(self.backer)
        with (
            patch('projects.payment_views.is_stripe_configured', return_value=True),
            patch('projects.payment_views.retrieve_payment_intent', return_value=self._fake_intent(donation)),
        ):
            response = self.client.post(
                reverse('projects:project-donate-confirm', args=[project.id]),
                {'payment_intent_id': 'pi_test_123'},
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        donation.refresh_from_db()
        self.assertEqual(donation.status, Donation.STATUS_SUCCESSFUL)
        self.assertEqual(donation.transaction_id, 'pi_test_123')
        self.assertEqual(donation.card_brand, 'visa')
        self.assertEqual(donation.card_last4, '4242')
        project.refresh_from_db()
        self.assertEqual(project.current_fund, __import__('decimal').Decimal('120.50'))
        self.assertIn('transaction_id', response.data)

    def test_confirm_is_idempotent_against_webhook_race(self):
        project = self.create_project()
        donation = self._pending_donation(project)
        self.client.force_authenticate(self.backer)
        with (
            patch('projects.payment_views.is_stripe_configured', return_value=True),
            patch('projects.payment_views.retrieve_payment_intent', return_value=self._fake_intent(donation)),
        ):
            self.client.post(reverse('projects:project-donate-confirm', args=[project.id]), {'payment_intent_id': 'pi_test_123'})
            self.client.post(reverse('projects:project-donate-confirm', args=[project.id]), {'payment_intent_id': 'pi_test_123'})
        project.refresh_from_db()
        self.assertEqual(project.current_fund, __import__('decimal').Decimal('120.50'))
        self.assertEqual(Donation.objects.count(), 1)

    def test_confirm_declined_card_returns_402_and_no_fund(self):
        project = self.create_project()
        donation = self._pending_donation(project)
        self.client.force_authenticate(self.backer)
        declined = self._fake_intent(
            donation, status='requires_payment_method',
            last_error=SimpleNamespace(code='card_declined', message='Your card was declined.'),
        )
        with (
            patch('projects.payment_views.is_stripe_configured', return_value=True),
            patch('projects.payment_views.retrieve_payment_intent', return_value=declined),
        ):
            response = self.client.post(
                reverse('projects:project-donate-confirm', args=[project.id]),
                {'payment_intent_id': 'pi_test_123'},
            )
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(response.data['error_code'], 'card_declined')
        donation.refresh_from_db()
        self.assertEqual(donation.status, Donation.STATUS_FAILED)
        self.assertIn('card_declined', donation.failure_reason)
        project.refresh_from_db()
        self.assertEqual(project.current_fund, 0)

    def test_confirm_insufficient_funds_code_mapped(self):
        project = self.create_project()
        donation = self._pending_donation(project)
        self.client.force_authenticate(self.backer)
        intent = self._fake_intent(
            donation, status='requires_payment_method',
            last_error=SimpleNamespace(code='insufficient_funds', message='Your card has insufficient funds.'),
        )
        with (
            patch('projects.payment_views.is_stripe_configured', return_value=True),
            patch('projects.payment_views.retrieve_payment_intent', return_value=intent),
        ):
            response = self.client.post(
                reverse('projects:project-donate-confirm', args=[project.id]),
                {'payment_intent_id': 'pi_test_123'},
            )
        self.assertEqual(response.status_code, status.HTTP_402_PAYMENT_REQUIRED)
        self.assertEqual(response.data['error_code'], 'insufficient_funds')

    def test_confirm_rejects_wrong_owner(self):
        project = self.create_project()
        donation = self._pending_donation(project)
        self.client.force_authenticate(self.creator)  # different user than donation
        intent = self._fake_intent(donation, user_id=donation.user_id)  # metadata says backer
        with (
            patch('projects.payment_views.is_stripe_configured', return_value=True),
            patch('projects.payment_views.retrieve_payment_intent', return_value=intent),
        ):
            response = self.client.post(
                reverse('projects:project-donate-confirm', args=[project.id]),
                {'payment_intent_id': 'pi_test_123'},
            )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        donation.refresh_from_db()
        self.assertEqual(donation.status, Donation.STATUS_PENDING)

    def test_confirm_rejects_amount_mismatch(self):
        project = self.create_project()
        donation = self._pending_donation(project)
        self.client.force_authenticate(self.backer)
        intent = self._fake_intent(donation, amount=99999)
        with (
            patch('projects.payment_views.is_stripe_configured', return_value=True),
            patch('projects.payment_views.retrieve_payment_intent', return_value=intent),
        ):
            response = self.client.post(
                reverse('projects:project-donate-confirm', args=[project.id]),
                {'payment_intent_id': 'pi_test_123'},
            )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Donation.objects.get().status, Donation.STATUS_PENDING)

    def test_webhook_success_records_donation(self):
        project = self.create_project()
        donation = self._pending_donation(project)
        event = {
            'type': 'payment_intent.succeeded',
            'data': {
                'object': {
                    'id': 'pi_webhook_1',
                    'metadata': {'donation_id': str(donation.id)},
                    'payment_method_details': {'card': {'brand': 'mastercard', 'last4': '0005'}},
                }
            },
        }
        with (
            patch('projects.payment_views.is_stripe_configured', return_value=True),
            patch('projects.payment_views.verify_webhook_event', return_value=event),
        ):
            response = self.client.post(
                reverse('projects:payment-webhook'),
                data=b'ignored-raw-payload',
                HTTP_STRIPE_SIGNATURE='t=1,v1=fake',
                content_type='application/json',
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        donation.refresh_from_db()
        self.assertEqual(donation.status, Donation.STATUS_SUCCESSFUL)
        self.assertEqual(donation.transaction_id, 'pi_webhook_1')
        self.assertEqual(donation.card_brand, 'mastercard')
        project.refresh_from_db()
        self.assertEqual(project.current_fund, __import__('decimal').Decimal('120.50'))

    def test_webhook_failed_event_marks_donation_failed(self):
        project = self.create_project()
        donation = self._pending_donation(project)
        event = {
            'type': 'payment_intent.payment_failed',
            'data': {
                'object': {
                    'id': 'pi_failed_1',
                    'metadata': {'donation_id': str(donation.id)},
                    'last_payment_error': {'code': 'card_declined', 'message': 'Your card was declined.'},
                }
            },
        }
        with (
            patch('projects.payment_views.is_stripe_configured', return_value=True),
            patch('projects.payment_views.verify_webhook_event', return_value=event),
        ):
            response = self.client.post(
                reverse('projects:payment-webhook'),
                data=b'ignored-raw-payload',
                HTTP_STRIPE_SIGNATURE='t=1,v1=fake',
                content_type='application/json',
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        donation.refresh_from_db()
        self.assertEqual(donation.status, Donation.STATUS_FAILED)
        self.assertEqual(project.current_fund, 0)

    def test_webhook_invalid_signature_rejected(self):
        project = self.create_project()
        self._pending_donation(project)
        with (
            patch('projects.payment_views.is_stripe_configured', return_value=True),
            patch('projects.payment_views.verify_webhook_event', side_effect=GatewayError('bad signature')),
        ):
            response = self.client.post(
                reverse('projects:payment-webhook'),
                data=b'bad',
                HTTP_STRIPE_SIGNATURE='t=1,v1=bad',
                content_type='application/json',
            )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ScopingTests(ProjectTestCase):

    def test_my_projects_only_returns_own(self):
        mine = self.create_project(title='مشروعي')
        self.create_project(title='مشروع غيري', creator=self.backer)
        self.client.force_authenticate(self.creator)
        response = self.client.get(reverse('projects:my-projects'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [item['title'] for item in response.data['results']]
        self.assertEqual(titles, ['مشروعي'])
        self.assertNotIn('مشروع غيري', titles)

    def test_my_donations_only_returns_own(self):
        project = self.create_project()
        Donation.objects.create(
            user=self.backer, project=project, amount='25.00',
            status=Donation.STATUS_SUCCESSFUL,
        )
        Donation.objects.create(
            user=self.creator, project=project, amount='75.00',
            status=Donation.STATUS_SUCCESSFUL,
        )
        self.client.force_authenticate(self.backer)
        response = self.client.get(reverse('projects:my-donations'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        amounts = [item['amount'] for item in response.data['results']]
        self.assertEqual(amounts, ['25.00'])
        # History now carries the payment status + gateway reference.
        row = response.data['results'][0]
        self.assertEqual(row['status'], 'successful')
        self.assertIn('transaction_id', row)
        self.assertIsNone(row['payment_method'])
        self.assertEqual(row['currency'], 'EGP')
        self.assertIn('created_at', row)


class UpdateRewardTests(ProjectTestCase):

    def test_creator_posts_update(self):
        project = self.create_project()
        self.client.force_authenticate(self.creator)
        response = self.client.post(
            reverse('projects:project-updates', args=[project.id]),
            {'title': 'تقرير أول', 'body': 'خلصنا المرحلة الأولى'},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(ProjectUpdate.objects.filter(project=project).exists())

    def test_non_creator_cannot_post_update(self):
        project = self.create_project()
        self.client.force_authenticate(self.backer)
        response = self.client.post(
            reverse('projects:project-updates', args=[project.id]),
            {'title': 'دخيل', 'body': 'x'},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_creator_adds_reward_tier(self):
        project = self.create_project()
        self.client.force_authenticate(self.creator)
        response = self.client.post(
            reverse('projects:project-rewards', args=[project.id]),
            {'title': 'شكر على الدعم', 'amount': '50.00', 'description': 'بطاقة شكر'},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(RewardTier.objects.filter(project=project).exists())

    def test_reward_tier_amount_must_be_positive(self):
        project = self.create_project()
        self.client.force_authenticate(self.creator)
        response = self.client.post(
            reverse('projects:project-rewards', args=[project.id]),
            {'title': 'صفر', 'amount': '0'},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reward_backers_count_only_successful_donations(self):
        project = self.create_project()
        RewardTier.objects.create(project=project, title='شكر على الدعم', amount='50.00')
        Donation.objects.create(
            user=self.backer, project=project, amount='100.00',
            status=Donation.STATUS_SUCCESSFUL,
        )
        Donation.objects.create(
            user=self.creator, project=project, amount='100.00',  # pending
        )
        response = self.client.get(reverse('projects:project-rewards', args=[project.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'][0]['backers'], 1)


class SimilarProjectTests(ProjectTestCase):

    def test_similar_projects_ranked_by_shared_tags(self):
        tag_a = Tag.objects.create(name='تعليم')
        tag_b = Tag.objects.create(name='صحة')
        base = self.create_project(title='الأساس')
        base.tags.add(tag_a, tag_b)

        shares_both = self.create_project(title='يشترك في الاتنين', creator=self.backer)
        shares_both.tags.add(tag_a, tag_b)
        shares_one = self.create_project(title='يشترك في واحد', creator=self.backer)
        shares_one.tags.add(tag_a)

        similar = base.similar_projects()
        self.assertEqual([p.title for p in similar], ['يشترك في الاتنين', 'يشترك في واحد'])