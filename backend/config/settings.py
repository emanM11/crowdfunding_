"""
Django settings for the Crowdfunding Platform backend (API only).
See PROJECT_SPEC.md sections 2, 3, 5.1, 7, 8, 9, 10, 12 for the decisions
encoded here.
"""

from pathlib import Path
from datetime import timedelta
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='127.0.0.1,localhost', cast=Csv())

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',

    # local apps
    'accounts',
    'projects',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # must sit above CommonMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ---------------------------------------------------------------------------
# Database — PostgreSQL, configured via .env (see PROJECT_SPEC.md 3, 5)
# ---------------------------------------------------------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='crowdfunding_db'),
        'USER': config('DB_USER', default='postgres'),
        'PASSWORD': config('DB_PASSWORD', default='postgres'),
        'HOST': config('DB_HOST', default='127.0.0.1'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

# ---------------------------------------------------------------------------
# Custom user model — MUST be set before the first migration ever runs
# (PROJECT_SPEC.md section 15, step 5)
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = 'accounts.User'

# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ---------------------------------------------------------------------------
# Internationalization — Egypt timezone, timezone-aware datetimes everywhere
# (PROJECT_SPEC.md section 12)
# ---------------------------------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Cairo'
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static & media files
# ---------------------------------------------------------------------------
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------------
# CORS — allow the React dev server to call the API (PROJECT_SPEC.md 2)
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='http://localhost:5173', cast=Csv())

# React route base used to build activation / password-reset links in emails
FRONTEND_URL = config('FRONTEND_URL', default='http://localhost:5173')

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ) if not DEBUG else (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ),
    # Security hardening (PROJECT_SPEC.md 16): throttle brute-force /
    # spam-prone endpoints. 'register' and 'login' scopes are applied
    # explicitly on those views (accounts/views.py); everything
    # authenticated additionally gets a generous general ceiling.
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.ScopedRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'register': '5/hour',
        'login': '10/minute',
        'activate': '10/hour',
        'password_reset': '5/hour',
        'user': '300/minute',
    },
}

# ---------------------------------------------------------------------------
# Simple JWT (PROJECT_SPEC.md section 7)
# ---------------------------------------------------------------------------
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': False,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# ---------------------------------------------------------------------------
# Email — real Gmail SMTP for activation / password-reset emails
# (PROJECT_SPEC.md 5.1).
#
# The backend is SMTP by default and the parameters already point at Gmail
# (smtp.gmail.com:587, STARTTLS). Fill the real credentials in backend/.env:
#
#   EMAIL_HOST_USER=<your-app-gmail-address>            # e.g. crowdfunding@...
#   EMAIL_HOST_PASSWORD=<16-char-Gmail-App-Password>    # NOT your login password
#   DEFAULT_FROM_EMAIL='تكاتف <crowdfunding@...>'
#
# Gmail App Password (required, since the account has 2-Step Verification):
#   1. Create a dedicated Gmail account for the app.
#   2. myaccount.google.com/security  -> turn on 2-Step Verification.
#   3. myaccount.google.com/apppasswords -> generate a 16-char App Password.
#   4. Paste the App Password (spaces removed) into EMAIL_HOST_PASSWORD in .env.
#
# Safety fallback: while DEBUG=True and no EMAIL_HOST_USER is configured the
# backend silently stays on the console backend so `runserver` still prints
# every activation/reset email (and link) to the terminal instead of raising
# SMTPAuthenticationError on a blank password.
#
# Gotcha: `fail_silently=False` (accounts/utils.py) means a wrong
# password/Host makes registration return HTTP 500 — intentional, it
# surfaces broken SMTP config immediately rather than silently dropping
# every activation email.
# ---------------------------------------------------------------------------
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='YOUR_GMAIL_ADDRESS')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config(
    'DEFAULT_FROM_EMAIL', default='تكاتف <YOUR_GMAIL_ADDRESS>'
)

# No real inbox configured yet while we're still in development → print the
# emails to the terminal so the flow stays testable without credentials.
if DEBUG and not EMAIL_HOST_USER:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ---------------------------------------------------------------------------
# Logging — the accounts app logs every activation / password-reset link it
# sends at INFO level. With the console email backend these links are already
# printed inside the raw email, but this line makes them unmistakable in the
# runserver terminal so they can be clicked straight away in dev.
# ---------------------------------------------------------------------------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'accounts': {
            'handlers': ['console'],
            # Reset links are sensitive — silent by default in production,
            # loud during development.
            'level': 'INFO' if DEBUG else 'WARNING',
        },
    },
}

# ---------------------------------------------------------------------------
# Token / link expiry (PROJECT_SPEC.md 5.1): 24 hours for both the account
# activation link and the password-reset link. Django's stdlib setting name
# (PASSWORD_RESET_TIMEOUT, seconds) is used for password reset so the
# built-in helpers agree with our custom token check.
# ---------------------------------------------------------------------------
ACTIVATION_TOKEN_LIFETIME_HOURS = 24
PASSWORD_RESET_TIMEOUT = 86400  # 24 hours = 24 * 60 * 60 seconds

# Bonus: Facebook login (PROJECT_SPEC.md 5.1). Empty by default — the
# facebook login endpoint responds 503 until real app credentials are set
# in .env, rather than silently accepting unverifiable tokens.
FACEBOOK_APP_ID = config('FACEBOOK_APP_ID', default='')
FACEBOOK_APP_SECRET = config('FACEBOOK_APP_SECRET', default='')

# ---------------------------------------------------------------------------
# Payment gateway (PROJECT_SPEC.md 5.6 donation upgrade)
#
#   PAYMENT_GATEWAY=mock    (default) — fully offline gateway that behaves
#                           like Stripe test mode: process_payment validates
#                           the card (Luhn / expiry / CVC) and approves every
#                           card except Stripe's decline test card
#                           4000 0000 0000 0002. No keys, no network.
#   PAYMENT_GATEWAY=stripe — real Stripe test-mode API. The browser
#                           tokenizes the card with Stripe Elements
#                           (frontend env VITE_STRIPE_PUBLIC_KEY), the backend
#                           charges via the PaymentIntents API and verifies
#                           completion server-side and via webhook. Requires:
#                             STRIPE_SECRET_KEY=sk_test_...
#                             STRIPE_WEBHOOK_SECRET=whsec_...  (for webhook)
#
# Card data is tokenized client-side and is NEVER stored; only the masked
# last-4 + cardholder name are kept on the Donation row for auditing.
# ---------------------------------------------------------------------------
PAYMENT_GATEWAY = config('PAYMENT_GATEWAY', default='mock')
STRIPE_SECRET_KEY = config('STRIPE_SECRET_KEY', default='')
STRIPE_WEBHOOK_SECRET = config('STRIPE_WEBHOOK_SECRET', default='')

# ---------------------------------------------------------------------------
# Production hardening — only kicks in once DEBUG=False in .env, so local
# development over plain http:// is unaffected (PROJECT_SPEC.md 16).
# ---------------------------------------------------------------------------
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
