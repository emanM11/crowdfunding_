from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer as TokenObtainPairSerializerBase

User = get_user_model()

MAX_IMAGE_SIZE_MB = 5


class TokenObtainPairSerializer(TokenObtainPairSerializerBase):
    """
    Login serializer. On top of SimpleJWT's behaviour it rejects accounts
    that exist but have NOT activated their email yet with a clear Arabic
    message instead of the generic "no active account" one.

    Security note: the friendly message only fires when the submitted
    password is correct. A wrong password (or unknown email) still gets the
    generic error, so the endpoint cannot be used to enumerate which emails
    are registered or whether an account is just dormant.
    """

    INACTIVE_ACCOUNT_MESSAGE = 'حسابك غير مفعّل. يرجى مراجعة بريدك الإلكتروني لتفعيل الحساب.'

    def validate(self, attrs):
        UserModel = get_user_model()
        try:
            candidate = UserModel._default_manager.get_by_natural_key(
                attrs[self.username_field]
            )
        except UserModel.DoesNotExist:
            candidate = None

        if (
            candidate is not None
            and not candidate.is_active
            and candidate.check_password(attrs['password'])
        ):
            raise AuthenticationFailed(self.INACTIVE_ACCOUNT_MESSAGE)

        return super().validate(attrs)


def validate_image_size(image):
    """Shared upload guard — PROJECT_SPEC.md 16 security hardening: reject
    oversized uploads before they ever hit disk/S3."""
    if image.size > MAX_IMAGE_SIZE_MB * 1024 * 1024:
        raise serializers.ValidationError(f'Image must be {MAX_IMAGE_SIZE_MB}MB or smaller.')
    return image


class RegisterSerializer(serializers.ModelSerializer):
    """
    PROJECT_SPEC.md 5.1 / 6.1.
    confirm_password is validation-only and is never stored.
    """
    confirm_password = serializers.CharField(write_only=True)
    # Runs through Django's configured AUTH_PASSWORD_VALIDATORS (settings.py)
    # — not just a length check — so this rejects common/numeric-only/
    # too-similar-to-email passwords the same way `createsuperuser` would.
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'first_name', 'last_name', 'email',
            'password', 'confirm_password', 'phone_number',
            'profile_picture', 'is_active',
        ]
        read_only_fields = ['id', 'is_active']

    def validate_profile_picture(self, image):
        return validate_image_size(image) if image else image

    def validate(self, attrs):
        if attrs['password'] != attrs.pop('confirm_password'):
            raise serializers.ValidationError(
                {'confirm_password': ['Passwords do not match.']}
            )
        # Build a throwaway user so validators that compare the password
        # against user attributes (email similarity, etc.) work correctly.
        temp_user = User(
            email=attrs.get('email'),
            first_name=attrs.get('first_name'),
            last_name=attrs.get('last_name'),
        )
        validate_password(attrs['password'], user=temp_user)
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.is_active = False
        user.generate_activation_token()
        user.save()
        return user


class ProfileSerializer(serializers.ModelSerializer):
    """
    GET/PUT own profile. `email` is intentionally read-only here — this is
    the server-side enforcement PROJECT_SPEC.md 5.1 requires: no matter what
    the frontend sends or disables, email changes submitted through this
    serializer are silently ignored rather than applied.
    """

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'phone_number',
            'profile_picture', 'bio', 'birthdate', 'facebook_profile', 'country',
        ]
        read_only_fields = ['id', 'email']

    def validate_profile_picture(self, image):
        return validate_image_size(image) if image else image


class AccountDeleteSerializer(serializers.Serializer):
    """
    Bonus (PROJECT_SPEC.md 5.1): re-enter password to confirm deletion.
    Required for accounts that have a usable password. Facebook-only
    accounts (no password ever set) skip this check — there is nothing to
    re-enter — and delete on confirmation alone.

    The check is deliberately in `validate()` (object-level), not a
    `validate_password` field method: a field-level validator only runs
    when the field is present in the request body, so with `required=False`
    a request that omits the `password` key entirely would skip the check
    completely and delete the account unauthenticated-by-password. Object-
    level validation always runs, so a missing key is treated the same as
    a wrong one.
    """
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    def validate(self, attrs):
        user = self.context['request'].user
        if not user.has_usable_password():
            return attrs
        password = attrs.get('password', '')
        if not password or not user.check_password(password):
            raise serializers.ValidationError({'password': ['Incorrect password.']})
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': ['Passwords do not match.']})
        validate_password(attrs['password'], user=self.context['reset_user'])
        return attrs
