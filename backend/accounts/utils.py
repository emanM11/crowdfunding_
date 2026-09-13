import logging
from django.conf import settings
from django.core.mail import send_mail
import requests

logger = logging.getLogger(__name__)


def send_activation_email(user):
    """
    Sends the activation link email. Points to a React route
    (FRONTEND_URL/activate/<uid>/<token>) which then calls the activation
    endpoint on mount — PROJECT_SPEC.md 5.1.
    """
    activation_link = (
        f"{settings.FRONTEND_URL}/activate/{user.pk}/{user.activation_token}"
    )
    # Printed straight to the runserver terminal in dev (see LOGGING in
    # settings.py) so the link can be clicked without hunting through the
    # raw email dump.
    logger.info('Activation link for %s: %s', user.email, activation_link)
    send_mail(
        subject="فعّل حسابك في منصة التمويل الجماعي",
        message=(
            f"أهلاً {user.first_name},\n\n"
            f"من فضلك فعّل حسابك بالضغط على الرابط ده خلال 24 ساعة:\n"
            f"{activation_link}\n\n"
            f"لو مطلبتش تفعيل الحساب، تجاهل الإيميل ده."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


def send_password_reset_email(user):
    """Bonus (PROJECT_SPEC.md 5.1): points to a React route
    (FRONTEND_URL/reset-password/<uid>/<token>) that collects the new
    password and calls the confirm endpoint."""
    reset_link = (
        f"{settings.FRONTEND_URL}/reset-password/{user.pk}/{user.password_reset_token}"
    )
    # Explicit one-line log (see LOGGING in settings.py): in dev this is the
    # whole point — copy the printed URL into the browser to test the flow.
    logger.info('Password reset link for %s: %s', user.email, reset_link)
    send_mail(
        subject="استعادة كلمة المرور — تكاتف",
        message=(
            f"أهلاً {user.first_name},\n\n"
            f"اطلبت استعادة كلمة المرور. اضغط على الرابط ده خلال 24 ساعة "
            f"عشان تختار كلمة مرور جديدة:\n"
            f"{reset_link}\n\n"
            f"لو مطلبتش ده، تجاهل الإيميل ده — كلمة مرورك هتفضل زي ما هي."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


def verify_facebook_token(access_token):
    """
    Bonus (PROJECT_SPEC.md 5.1). Two calls, both required for safety:
    1. debug_token, signed with OUR app secret, confirms the token is
       valid *and* was issued to *our* Facebook app — without this check,
       any valid Facebook token from any app would be accepted, letting
       someone log in as an identity they don't control.
    2. /me fetches the profile the now-verified token belongs to.
    Returns the profile dict, or None if the token fails verification.
    """
    app_access_token = f"{settings.FACEBOOK_APP_ID}|{settings.FACEBOOK_APP_SECRET}"
    try:
        debug = requests.get(
            'https://graph.facebook.com/debug_token',
            params={'input_token': access_token, 'access_token': app_access_token},
            timeout=5,
        ).json().get('data', {})
    except requests.RequestException:
        return None

    if not debug.get('is_valid') or str(debug.get('app_id')) != str(settings.FACEBOOK_APP_ID):
        return None

    try:
        profile = requests.get(
            'https://graph.facebook.com/me',
            params={'fields': 'id,email,first_name,last_name', 'access_token': access_token},
            timeout=5,
        ).json()
    except requests.RequestException:
        return None

    return profile if 'id' in profile else None
