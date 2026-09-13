"""
Payment endpoint views for the Stripe PaymentIntents flow
(PROJECT_SPEC.md 5.6 + production-grade payment upgrade).

Flow (stripe mode, when PAYMENT_GATEWAY=stripe + STRIPE_SECRET_KEY are set):
    POST /api/payments/config/               -> {gateway: 'stripe'|'mock'}
    POST /api/projects/<id>/donate/process/  -> pending Donation + PaymentIntent;
                                                returns {client_secret, donation_id}
    POST /api/projects/<id>/donate/confirm/  -> backend re-verifies the intent and,
                                                only on status 'succeeded', marks the
                                                donation successful + raises current_fund
    POST /api/payments/webhook/              -> Stripe's idempotent source of truth

Cards are tokenized in the browser (Stripe Elements) and never reach these
endpoints. Marking successful is guarded so the confirm endpoint and the
webhook can race safely without double-counting current_fund.
"""

from django.db import transaction
from django.db.models import F
from rest_framework import permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Donation, Project
from .payments import (
    GatewayError,
    _minor_units,
    card_brand_from_intent,
    is_stripe_configured,
    payment_intent_result,
    retrieve_payment_intent,
    verify_webhook_event,
)
from .serializers import DonationHistorySerializer


def _commit_success(donation, transaction_id, brand='', last4=''):
    """
    Idempotent + race-safe commit of a confirmed payment: only the pending
    row that actually flips to 'successful' raises current_fund, so neither
    the confirm endpoint nor the webhook can double-count.
    Returns True when this call performed the flip, False when the donation
    was already recorded.
    """
    with transaction.atomic():
        flipped = Donation.objects.filter(
            pk=donation.pk, status=Donation.STATUS_PENDING
        ).update(
            status=Donation.STATUS_SUCCESSFUL,
            transaction_id=transaction_id,
            gateway='stripe',
            failure_reason='',
            card_brand=brand,
            card_last4=last4,
        )
        if flipped:
            Project.objects.filter(pk=donation.project_id).update(
                current_fund=F('current_fund') + donation.amount
            )
    return bool(flipped)


def _commit_failed(donation, error_code, message):
    if donation.status == Donation.STATUS_PENDING:
        donation.status = Donation.STATUS_FAILED
        donation.gateway = 'stripe'
        donation.failure_reason = ' | '.join(x for x in (error_code, message) if x)
        donation.save(update_fields=['status', 'gateway', 'failure_reason'])


class PaymentConfigView(APIView):
    """
    GET /api/payments/config/ — lets the checkout modal decide between the
    Stripe Elements flow and the offline sandbox card form. Only the gateway
    name is exposed; keys stay out of the API (the frontend reads its own
    public key from VITE_STRIPE_PUBLIC_KEY).
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({'gateway': 'stripe' if is_stripe_configured() else 'mock'})


class DonationConfirmView(APIView):
    """
    POST /api/projects/<id>/donate/confirm/
    Body: {"payment_intent_id": "pi_..."}

    The browser has already completed the card confirmation; this endpoint
    re-verifies the intent server-side (status must be 'succeeded', amount +
    currency + owner must match the pending donation) and only then commits
    the donation + raises current_fund. Declined / unfinished intents are
    archived as 'failed' donations (auditing) without moving any money.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        if not is_stripe_configured():
            return Response(
                {'detail': 'Payment gateway is not configured.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payment_intent_id = request.data.get('payment_intent_id') or ''
        if not payment_intent_id:
            raise ValidationError({'payment_intent_id': 'This field is required.'})

        try:
            intent = retrieve_payment_intent(payment_intent_id)
        except GatewayError:
            return Response(
                {'detail': 'Payment gateway is unavailable right now. Please try again later.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        metadata = getattr(intent, 'metadata', None) or {}
        donation_id = metadata.get('donation_id')
        if not donation_id:
            raise ValidationError({'payment_intent_id': 'No donation is linked to this payment.'})

        donation = (
            Donation.objects.filter(pk=int(donation_id))
            .select_related('project')
            .first()
        )
        if not donation or donation.user_id != request.user.id:
            raise ValidationError({'payment_intent_id': 'This payment does not belong to you.'})
        if str(metadata.get('user_id', '')) != str(request.user.id):
            raise ValidationError({'payment_intent_id': 'This payment does not belong to you.'})

        # Money reconciliation: the intent amount must be the donation's.
        if (
            getattr(intent, 'amount', None) != _minor_units(donation.amount, donation.currency)
            or getattr(intent, 'currency', None) != donation.currency.lower()
        ):
            raise ValidationError({'payment_intent_id': 'Payment amount does not match the donation.'})

        result = payment_intent_result(intent)

        if not result.success:
            _commit_failed(donation, result.error_code, result.error_message)
            return Response(
                {
                    'detail': result.error_message,
                    'error_code': result.error_code,
                    'donation': DonationHistorySerializer(donation, context={'request': request}).data,
                },
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )

        brand, last4 = card_brand_from_intent(intent)
        _commit_success(donation, result.transaction_id, brand, last4)
        donation.refresh_from_db()
        return Response(
            DonationHistorySerializer(donation, context={'request': request}).data,
            status=status.HTTP_200_OK,
        )


class PaymentWebhookView(APIView):
    """
    POST /api/payments/webhook/
    Stripe's server-to-server source of truth. The signature is verified
    against STRIPE_WEBHOOK_SECRET before anything is trusted. Handles
    payment_intent.succeeded / payment_intent.payment_failed idempotently —
    the same donation may arrive here and via /donate/confirm, and
    _commit_success keeps current_fund correct either way.
    """

    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    parser_classes = []  # verify the RAW body signature, never parsed JSON

    def post(self, request):
        if not is_stripe_configured():
            return Response(
                {'detail': 'Payment gateway is not configured.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sig_header = request.headers.get('Stripe-Signature', '')
        if not sig_header:
            return Response({'detail': 'Missing Stripe-Signature header.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            event = verify_webhook_event(request.body, sig_header)
        except GatewayError:
            return Response({'detail': 'Invalid signature.'}, status=status.HTTP_400_BAD_REQUEST)

        event_type = event['type'] if isinstance(event, dict) else getattr(event, 'type', '')
        stripe_object = event['data']['object'] if isinstance(event, dict) else event.data.object

        donation_id = stripe_object.get('metadata', {}).get('donation_id')
        if donation_id:
            try:
                donation = Donation.objects.filter(pk=int(donation_id)).select_related('project').first()
            except (TypeError, ValueError):
                donation = None
        else:
            donation = None

        if event_type == 'payment_intent.succeeded':
            if not donation:
                return Response({'detail': 'Unknown donation.'}, status=status.HTTP_400_BAD_REQUEST)
            brand, last4 = card_brand_from_intent(stripe_object)
            _commit_success(donation, stripe_object['id'], brand, last4)
            return Response({'status': 'ok'})

        if event_type == 'payment_intent.payment_failed':
            if donation:
                error = stripe_object.get('last_payment_error') or {}
                _commit_failed(donation, error.get('code', ''), error.get('message', ''))
            return Response({'status': 'ok'})

        return Response({'status': 'ignored'})