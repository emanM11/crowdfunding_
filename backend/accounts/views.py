from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import (
    AccountDeleteSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    ProfileSerializer,
    RegisterSerializer,
    TokenObtainPairSerializer,
)
from .utils import send_activation_email, send_password_reset_email, verify_facebook_token

User = get_user_model()


class ThrottledTokenObtainPairView(TokenObtainPairView):
    """Same as SimpleJWT's login view, with a scoped rate limit against
    credential-stuffing / brute-force (PROJECT_SPEC.md 16) and the custom
    serializer that explains unactivated accounts in Arabic."""
    serializer_class = TokenObtainPairSerializer
    throttle_scope = 'login'  # 10/minute per IP — see settings.py


class RegisterView(generics.CreateAPIView):
    """POST /api/auth/register/ — PROJECT_SPEC.md 6, 6.1."""
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    throttle_scope = 'register'  # 5/hour per IP — see settings.py

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        send_activation_email(user)
        # The agreed field list from PROJECT_SPEC.md 6.1 is preserved
        # (`id`, `email`, `is_active`); a `detail` key is added signalling
        # where to find the activation link. In dev it is printed on the
        # terminal (console email backend); in prod it lands in the inbox.
        return Response(
            {
                'id': user.id,
                'email': user.email,
                'is_active': user.is_active,
                'detail': (
                    f'Account created. An activation link has been sent to '
                    f'{user.email}. Click it within 24 hours to activate your '
                    'account. (In development, the link is printed to the '
                    'terminal console.)'
                ),
            },
            status=status.HTTP_201_CREATED,
        )


class ActivateView(APIView):
    """
    POST /api/auth/activate/<uid>/<token>/ — PROJECT_SPEC.md 5.1, 6, 6.1.
    uid binds the activation token to the account it was minted for; the
    token is invalidated (cleared) immediately after a successful
    activation so it can never be reused.
    """
    permission_classes = [permissions.AllowAny]
    throttle_scope = 'activate'  # 10/hour per IP — see settings.py

    def post(self, request, uid, token):
        try:
            user = User.objects.get(pk=uid, activation_token=token)
        except User.DoesNotExist:
            return Response(
                {'detail': 'This activation link is invalid or has already been used.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user.is_active:
            return Response({'detail': 'Your account is already activated. You can log in.'})

        if user.is_activation_token_expired:
            return Response(
                {'detail': 'This activation link has expired. Please register again to receive a new link.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.is_active = True
        user.clear_activation_token()
        user.save(update_fields=['is_active', 'activation_token', 'activation_token_created_at'])
        return Response({'detail': 'Your account has been activated. You can now log in.'})


class ProfileView(APIView):
    """
    GET/PUT /api/auth/profile/  — view/edit own profile (email locked).
    DELETE /api/auth/profile/   — soft-delete own account.
    PROJECT_SPEC.md 5.1, 6.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = ProfileSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        # partial=True: PUT here still behaves as a partial update since the
        # user is only expected to send the fields they're changing; email
        # is read_only on the serializer regardless of what's submitted.
        serializer = ProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request):
        serializer = AccountDeleteSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        # Soft-delete strategy (PROJECT_SPEC.md 5.1): never hard-delete, so
        # donation history and project data tied to this user are preserved.
        # Once `projects`/`donations` exist, their creator/user FKs stay
        # intact and simply point at this now-anonymized, inactive account.
        user.is_active = False
        user.email = f'deleted-user-{user.id}@deleted.local'
        user.first_name = 'Deleted'
        user.last_name = 'User'
        user.phone_number = '00000000000'
        user.profile_picture = None
        user.facebook_profile = None
        user.facebook_id = None
        user.set_unusable_password()
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PasswordResetRequestView(APIView):
    """
    POST /api/auth/password-reset/ — bonus (PROJECT_SPEC.md 5.1).
    Always responds with the same generic message whether or not the email
    exists — confirming/denying an account's existence here would let
    someone enumerate registered emails.
    """
    permission_classes = [permissions.AllowAny]
    throttle_scope = 'password_reset'  # 5/hour per IP — see settings.py

    GENERIC_RESPONSE = {
        'detail': 'If an account exists for this email, a reset link has been sent.'
    }

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(
            email=serializer.validated_data['email'], is_active=True
        ).first()
        if user:
            user.generate_password_reset_token()
            user.save(update_fields=['password_reset_token', 'password_reset_token_created_at'])
            send_password_reset_email(user)
        return Response(self.GENERIC_RESPONSE)


class PasswordResetConfirmView(APIView):
    """POST /api/auth/password-reset/confirm/<uid>/<token>/ — bonus
    (PROJECT_SPEC.md 5.1). Both the user id and the single-use token are
    in the URL; uid binds the token to the account the reset link was
    minted for. Token is cleared immediately on success, same pattern as
    activation."""
    permission_classes = [permissions.AllowAny]
    throttle_scope = 'password_reset'

    def post(self, request, uid, token):
        user = User.objects.filter(pk=uid, password_reset_token=token).first()
        if not user or user.is_password_reset_token_expired:
            return Response(
                {'detail': 'This reset link is invalid or has expired.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = PasswordResetConfirmSerializer(
            data=request.data, context={'reset_user': user}
        )
        serializer.is_valid(raise_exception=True)

        user.set_password(serializer.validated_data['password'])
        user.clear_password_reset_token()
        user.save()
        return Response({'detail': 'Password has been reset. You can now log in.'})


class FacebookLoginView(APIView):
    """
    POST /api/auth/facebook/ — bonus (PROJECT_SPEC.md 5.1).
    Expects {"access_token": "<token from the Facebook JS SDK>"}.
    Responds 503 until FACEBOOK_APP_ID/FACEBOOK_APP_SECRET are configured —
    silently accepting tokens we can't verify would be worse than refusing.
    """
    permission_classes = [permissions.AllowAny]
    throttle_scope = 'login'

    def post(self, request):
        if not settings.FACEBOOK_APP_ID or not settings.FACEBOOK_APP_SECRET:
            return Response(
                {'detail': 'Facebook login is not configured on this server.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        access_token = request.data.get('access_token')
        if not access_token:
            return Response({'detail': 'access_token is required.'}, status=status.HTTP_400_BAD_REQUEST)

        profile = verify_facebook_token(access_token)
        if not profile:
            return Response({'detail': 'Invalid or expired Facebook token.'}, status=status.HTTP_400_BAD_REQUEST)

        facebook_id = profile['id']
        user = User.objects.filter(facebook_id=facebook_id).first()

        if not user:
            email = profile.get('email')
            if not email:
                return Response(
                    {'detail': 'Your Facebook account has no email to link. Please register with email instead.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': profile.get('first_name', ''),
                    'last_name': profile.get('last_name', ''),
                    'phone_number': '',
                    'is_active': True,
                    'facebook_id': facebook_id,
                },
            )
            if created:
                user.set_unusable_password()
                user.save()
            elif not user.facebook_id:
                # An email/password account with a matching email — link
                # it rather than creating a duplicate. Does not touch their
                # existing password.
                user.facebook_id = facebook_id
                user.is_active = True
                user.save(update_fields=['facebook_id', 'is_active'])

        if not user.is_active:
            return Response(
                {'detail': 'This account is deactivated.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        refresh = RefreshToken.for_user(user)
        return Response({'access': str(refresh.access_token), 'refresh': str(refresh)})
