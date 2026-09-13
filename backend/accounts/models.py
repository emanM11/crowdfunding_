import secrets

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from .managers import UserManager
from .validators import egyptian_phone_validator


class User(AbstractUser):
    """
    Custom user model. Email is the login identifier (PROJECT_SPEC.md 5.1).
    `username` from AbstractUser is dropped entirely so there is only one
    identity field to keep in sync.
    """

    username = None
    email = models.EmailField('email address', unique=True)

    phone_number = models.CharField(
        max_length=11,
        validators=[egyptian_phone_validator],
        help_text='Egyptian mobile number, e.g. 01012345678',
    )
    profile_picture = models.ImageField(
        upload_to='profile_pictures/', blank=True, null=True
    )
    bio = models.TextField(blank=True, default='')

    # Registration must start inactive; login is blocked until activation.
    is_active = models.BooleanField(default=False)
    activation_token = models.CharField(
        max_length=64, unique=True, blank=True, null=True
    )
    activation_token_created_at = models.DateTimeField(blank=True, null=True)

    # Bonus: password reset (PROJECT_SPEC.md 5.1). Deliberately a separate
    # token/timestamp pair from activation — an already-active user
    # resetting their password must not disturb (or be blocked by) the
    # activation token fields, and vice versa.
    password_reset_token = models.CharField(max_length=64, unique=True, blank=True, null=True)
    password_reset_token_created_at = models.DateTimeField(blank=True, null=True)

    # Bonus: Facebook login (PROJECT_SPEC.md 5.1). Null for every account
    # created through normal email/password registration.
    facebook_id = models.CharField(max_length=64, unique=True, blank=True, null=True)

    # Optional extra profile info (PROJECT_SPEC.md 5.1)
    birthdate = models.DateField(blank=True, null=True)
    facebook_profile = models.URLField(blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'phone_number']

    objects = UserManager()

    def __str__(self):
        return self.email

    def generate_activation_token(self):
        """
        Generate a new, non-guessable activation token and timestamp it.
        Called at registration, and safe to call again for a future
        resend-activation flow.
        """
        self.activation_token = secrets.token_urlsafe(32)
        self.activation_token_created_at = timezone.now()
        return self.activation_token

    @property
    def is_activation_token_expired(self):
        if not self.activation_token_created_at:
            return True
        lifetime_hours = getattr(settings, 'ACTIVATION_TOKEN_LIFETIME_HOURS', 24)
        expires_at = self.activation_token_created_at + timezone.timedelta(
            hours=lifetime_hours
        )
        return timezone.now() > expires_at

    def clear_activation_token(self):
        """Invalidate the token so it cannot be reused after activation."""
        self.activation_token = None
        self.activation_token_created_at = None

    def generate_password_reset_token(self):
        """Same non-guessable, single-use, time-boxed pattern as activation
        — see generate_activation_token()."""
        self.password_reset_token = secrets.token_urlsafe(32)
        self.password_reset_token_created_at = timezone.now()
        return self.password_reset_token

    @property
    def is_password_reset_token_expired(self):
        if not self.password_reset_token_created_at:
            return True
        # Django's stdlib PASSWORD_RESET_TIMEOUT is in seconds (settings.py
        # sets it to 86400 = 24h), matching the activation window.
        timeout_seconds = getattr(settings, 'PASSWORD_RESET_TIMEOUT', 86400)
        expires_at = self.password_reset_token_created_at + timezone.timedelta(
            seconds=timeout_seconds
        )
        return timezone.now() > expires_at

    def clear_password_reset_token(self):
        self.password_reset_token = None
        self.password_reset_token_created_at = None
