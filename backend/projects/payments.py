"""
Payment gateway abstraction for donations (PROJECT_SPEC.md 5.6 payment
upgrade). Two modes, selected by ``settings.PAYMENT_GATEWAY``:

* ``mock`` (default) — a fully offline gateway that behaves like Stripe in
  test mode. The card is entered in a sandbox form, validated server-side
  (Luhn / expiry / CVC) and approved for every card except Stripe's
  documented decline card 4000 0000 0000 0002. No keys, no network.

* ``stripe`` — real Stripe test-mode via the PaymentIntents API, with the
  card tokenized CLIENT-SIDE by Stripe Elements (the browser plays the raw
  card details into Stripe's iframes using the public key), so the backend
  never sees a card number:
    1. POST /donate/process/  -> creates a pending Donation + PaymentIntent
       (returns ``client_secret``).
    2. Browser confirms the intent (confirmCardPayment).
    3. POST /donate/confirm/  -> backend re-verifies the intent via the API
       and only then marks the donation successful + raises current_fund.
    4. payments/webhook/      -> Stripe's idempotent source of truth.

PCI note: card numbers are never persisted (not even masked from raw input
in Stripe mode — the last-4 comes from the intent's payment method, as does
the card brand).

Sandbox-mode helpers (mock) that touch card numbers exist strictly for local
development and ship nothing to the user-facing flow in Stripe mode.
"""

import random
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP

from django.conf import settings

# Stripe's documented test cards (https://docs.stripe.com/testing):
TEST_CARD_SUCCESS = '4242424242424242'      # approved every time
TEST_CARD_DECLINED = '4000000000000002'     # always declined

_NUMBER_RE = re.compile(r'^[0-9]{13,19}$')
_EXPIRY_RE = re.compile(r'^(0[1-9]|1[0-2])/([0-9]{2})$')
_CVC_RE = re.compile(r'^[0-9]{3,4}$')


class PaymentError(Exception):
    """A card-detail validation failure caught server-side after the client
    check (defense in depth). ``field`` maps to the serializer key."""

    def __init__(self, field, message):
        self.field = field
        self.message = message
        super().__init__(message)


class GatewayError(Exception):
    """The gateway itself failed (network down, Stripe auth, Stripe API
    error) — not the card's fault. The caller reports a 5xx so the user can
    retry instead of being told their card is bad."""


@dataclass
class PaymentResult:
    success: bool
    gateway: str
    transaction_id: str = ''      # gateway reference, saved for auditing
    error_code: str = ''          # e.g. card_declined / insufficient_funds
    error_message: str = ''       # human-readable failure reason


def is_stripe_configured():
    """True only when the developer opted into real Stripe AND provided a
    secret key; otherwise the platform silently runs the offline mock."""
    return (
        (settings.PAYMENT_GATEWAY or 'mock').lower() == 'stripe'
        and bool(settings.STRIPE_SECRET_KEY)
    )


# ---------------------------------------------------------------------------
# Sandbox (mock) card helpers — validation + the offline gateway.
# ---------------------------------------------------------------------------

def digits_only(value):
    """Strip the spaces/dashes users type, e.g. '4242 4242 4242 4242'."""
    return re.sub(r'[\s-]+', '', value or '')


def is_luhn_valid(number):
    """ISO/IEC 7812 Luhn checksum over a digit string."""
    total = 0
    for i, ch in enumerate(reversed(number)):
        n = int(ch)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def validate_card(card_number, card_expiry, card_cvc):
    """
    Server-side card validation for the mock/sandbox flow. Returns
    ``(digits, expiry_month, expiry_year)``. Raises ``PaymentError`` with the
    offending serializer field on the first problem.
    """
    number = digits_only(card_number)
    if not _NUMBER_RE.match(number):
        raise PaymentError('card_number', 'Invalid card number.')
    if not is_luhn_valid(number):
        raise PaymentError('card_number', 'Card number failed the Luhn check.')

    expiry_match = _EXPIRY_RE.match(card_expiry or '')
    if not expiry_match:
        raise PaymentError('card_expiry', 'Expiry must be in MM/YY format.')
    month, short_year = int(expiry_match.group(1)), int(expiry_match.group(2))
    year = 2000 + short_year
    now = datetime.now()
    if year < now.year or (year == now.year and month < now.month):
        raise PaymentError('card_expiry', 'Card is expired.')
    if year > now.year + 10:
        raise PaymentError('card_expiry', 'Expiry is too far in the future.')

    if not _CVC_RE.match(card_cvc or ''):
        raise PaymentError('card_cvc', 'CVC must be 3 or 4 digits.')

    return number, month, year


def process_mock_payment(*, amount, currency, card_number, card_expiry, card_cvc):
    """Offline gateway: approves any valid card except the Stripe decline
    test card. Returns a PaymentResult — the caller persists the outcome."""
    try:
        number, _, _ = validate_card(card_number, card_expiry, card_cvc)
    except PaymentError as exc:
        return PaymentResult(
            success=False, gateway='mock',
            error_code='invalid_card', error_message=exc.message,
        )
    if number == TEST_CARD_DECLINED:
        return PaymentResult(
            success=False, gateway='mock',
            error_code='card_declined',
            error_message='Your card was declined. Please use another card.',
        )
    return PaymentResult(
        success=True, gateway='mock',
        transaction_id='MOCK-{:%Y%m%d%H%M%S}-{:06d}'.format(
            datetime.utcnow(), random.randint(0, 999999)
        ),
    )


# ---------------------------------------------------------------------------
# Stripe PaymentIntents helpers (secured by client-side tokenization).
# ---------------------------------------------------------------------------

def _minor_units(amount, currency):
    """Whole amount in the currency's smallest unit (piastres/cents).
    EGP and USD are both 2-decimal currencies. Rounds half-up to keep the
    gateway charge and the stored decimal amount exact."""
    return int((amount * 100).to_integral_value(rounding=ROUND_HALF_UP))


def get_stripe():
    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


def create_payment_intent(*, amount, currency, donation_id, user_id):
    """
    Create an unconfirmed PaymentIntent whose confirmation is completed by
    the browser (Stripe Elements / confirmCardPayment). `metadata` ties the
    intent back to the pending Donation row so both the confirm endpoint and
    the webhook can verify + record idempotently.
    Returns ``(client_secret, payment_intent_id)``.
    """
    stripe = get_stripe()
    try:
        intent = stripe.PaymentIntent.create(
            amount=_minor_units(amount, currency),
            currency=currency.lower(),
            payment_method_types=['card'],
            metadata={'donation_id': str(donation_id), 'user_id': str(user_id)},
        )
    except Exception as exc:  # auth / network / Stripe API
        raise GatewayError('Stripe could not create the payment intent: %s' % exc) from exc
    return intent.client_secret, intent.id


def retrieve_payment_intent(payment_intent_id):
    """Fetch an intent from the gateway (also used by the webhook handler).
    Raises ``GatewayError`` when Stripe is unreachable."""
    stripe = get_stripe()
    try:
        return stripe.PaymentIntent.retrieve(payment_intent_id)
    except Exception as exc:
        raise GatewayError('Stripe is unreachable: %s' % exc) from exc


def payment_intent_result(intent):
    """
    Translate a retrieved PaymentIntent into a PaymentResult:
    only status='succeeded' is treated as money received. Declines surface
    their Stripe error code (card_declined / insufficient_funds / ...) so
    the frontend can show a targeted, user-friendly message.
    """
    status = getattr(intent, 'status', None)
    if status == 'succeeded':
        return PaymentResult(success=True, gateway='stripe', transaction_id=intent.id)

    error = getattr(intent, 'last_payment_error', None) or {}
    code = error.get('code') if isinstance(error, dict) else getattr(error, 'code', None)
    message = (
        error.get('message') if isinstance(error, dict)
        else getattr(error, 'message', None)
    )
    if not code:
        code = 'payment_%s' % (status or 'failed')
    return PaymentResult(
        success=False, gateway='stripe',
        error_code=code,
        error_message=message or 'The payment was not completed.',
    )


def verify_webhook_event(payload, sig_header):
    """
    Reconstruct a Stripe webhook event against STRIPE_WEBHOOK_SECRET — the
    only endpoint that never trusts an unverified request. Raises
    ``GatewayError`` (invalid signature) so views map it to HTTP 400.
    """
    stripe = get_stripe()
    try:
        return stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except Exception as exc:
        raise GatewayError('Invalid Stripe webhook signature: %s' % exc) from exc


def card_brand_from_intent(intent):
    """Brand + last-4 from the intent's payment method, e.g. 'visa'/'4242'.
    Never returned from raw card input — it comes from Stripe's tokenized
    payment method, which is the PCI-safe source. Accepts both the
    object-like PaymentIntent (retrieve/confirm) and the plain dict carried
    by a webhook event."""
    if isinstance(intent, dict):
        pm = intent.get('payment_method_details') or {}
        details = pm.get('card', {}) if isinstance(pm, dict) else {}
        brand = details.get('brand')
        last4 = details.get('last4')
    else:
        pm = getattr(intent, 'payment_method_details', None) or {}
        details = pm.get('card', {}) if isinstance(pm, dict) else getattr(pm, 'card', None) or {}
        brand = details.get('brand') if isinstance(details, dict) else getattr(details, 'brand', None)
        last4 = details.get('last4') if isinstance(details, dict) else getattr(details, 'last4', None)
    return (brand or ''), (last4 or '')