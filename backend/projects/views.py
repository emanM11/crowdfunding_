from django.db.models import F
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Category, Donation, Project, ProjectUpdate, RewardTier, Tag
from .payments import (
    GatewayError,
    create_payment_intent,
    digits_only,
    is_stripe_configured,
    process_mock_payment,
)
from .serializers import (
    CategorySerializer,
    DonationCreateSerializer,
    DonationHistorySerializer,
    DonationStartSerializer,
    ProjectCreateUpdateSerializer,
    ProjectDetailSerializer,
    ProjectListSerializer,
    ProjectUpdateSerializer,
    RewardTierSerializer,
    TagSerializer,
)


def _project_queryset():
    # PROJECT_SPEC.md 11 — avoid N+1 queries on list/detail views.
    return (
        Project.objects.select_related('category', 'creator')
        .prefetch_related('tags', 'images', 'donations', 'updates', 'rewards')
    )


class ProjectListCreateView(generics.ListCreateAPIView):
    """GET/POST /api/projects/ — PROJECT_SPEC.md 6."""
    queryset = _project_queryset()
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_serializer_class(self):
        return ProjectCreateUpdateSerializer if self.request.method == 'POST' else ProjectListSerializer

    def get_serializer_context(self):
        return {'request': self.request}


class ProjectDetailView(generics.RetrieveUpdateAPIView):
    """
    GET/PUT /api/projects/<id>/ — PUT verifies the authenticated user is
    the project creator (PROJECT_SPEC.md 6, 8).
    """
    queryset = _project_queryset()
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_serializer_class(self):
        return ProjectCreateUpdateSerializer if self.request.method in ('PUT', 'PATCH') else ProjectDetailSerializer

    def get_serializer_context(self):
        return {'request': self.request}

    def update(self, request, *args, **kwargs):
        project = self.get_object()
        if project.creator_id != request.user.id:
            raise PermissionDenied('You do not have permission to perform this action.')
        return super().update(request, *args, **kwargs)


class ProjectCancelView(APIView):
    """POST /api/projects/<id>/cancel/ — creator-only, enforces the strict
    <25% rule (PROJECT_SPEC.md 5.4, 8)."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        if project.creator_id != request.user.id:
            raise PermissionDenied('You do not have permission to perform this action.')
        if project.status == 'cancelled':
            return Response({'detail': 'Project is already cancelled.'}, status=status.HTTP_400_BAD_REQUEST)
        if not project.can_be_cancelled():
            return Response(
                {'detail': 'Project cannot be cancelled: donations have reached 25% or more of the target.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        project.cancel()
        return Response(ProjectDetailSerializer(project, context={'request': request}).data)


class MyProjectsView(generics.ListAPIView):
    """GET /api/projects/my-projects/ — PROJECT_SPEC.md 6, 10."""
    serializer_class = ProjectListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return _project_queryset().filter(creator=self.request.user)

    def get_serializer_context(self):
        return {'request': self.request}


class ProjectUpdateListCreateView(generics.ListCreateAPIView):
    """GET/POST /api/projects/<pk>/updates/ — creator posts progress notes.

    GET is read-only for everyone; POST requires the authenticated creator.
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_project(self):
        return get_object_or_404(Project, pk=self.kwargs['pk'])

    def get_queryset(self):
        return ProjectUpdate.objects.filter(project_id=self.kwargs['pk'])

    def get_serializer_class(self):
        return ProjectUpdateSerializer

    def get_serializer_context(self):
        return {'request': self.request}

    def create(self, request, *args, **kwargs):
        project = self.get_project()
        if project.creator_id != request.user.id:
            raise PermissionDenied('You do not have permission to perform this action.')
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        update = ProjectUpdate.objects.create(project=project, **serializer.validated_data)
        response_serializer = ProjectUpdateSerializer(update, context=self.get_serializer_context())
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
            headers=self.get_success_headers(response_serializer.data),
        )


class RewardTierListCreateView(generics.ListCreateAPIView):
    """GET/POST /api/projects/<pk>/rewards/ — creator manages funding tiers.

    GET is read-only for everyone; POST requires the authenticated creator.
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_project(self):
        return get_object_or_404(Project, pk=self.kwargs['pk'])

    def get_queryset(self):
        return RewardTier.objects.filter(project_id=self.kwargs['pk'])

    def get_serializer_class(self):
        return RewardTierSerializer

    def get_serializer_context(self):
        return {'request': self.request}

    def create(self, request, *args, **kwargs):
        project = self.get_project()
        if project.creator_id != request.user.id:
            raise PermissionDenied('You do not have permission to perform this action.')
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if serializer.validated_data.get('amount', 0) <= 0:
            raise ValidationError({'amount': 'amount must be greater than zero.'})
        tier = RewardTier.objects.create(project=project, **serializer.validated_data)
        response_serializer = RewardTierSerializer(tier, context=self.get_serializer_context())
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
            headers=self.get_success_headers(response_serializer.data),
        )


class DonationProcessView(APIView):
    """
    POST /api/projects/<id>/donate/process/ (and the /donate/ alias) —
    PROJECT_SPEC.md 5.6 donation + payment upgrade.

    Business rules enforced server-side, never trusted from the frontend:
    authenticated, project must be running & inside its date window,
    amount > 0, creator cannot donate to their own project.

    Two payment modes (projects/payments.py):
      * mock   — offline sandbox: card fields validated here (defense in
                 depth), charged through the mock gateway, donation marked
                 'successful' only on approval; current_fund raised
                 atomically.
      * stripe — client-side tokenization: the serializer carries NO card
                 fields; this endpoint creates a pending Donation + a
                 PaymentIntent and hands the browser a client_secret. The
                 donation is only committed by /donate/confirm/ (and the
                 webhook) after the intent truly succeeded.

    A client-generated idempotency_key prevents double-charging on a retried
    request. Full card numbers are never persisted.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk)

        if project.creator_id == request.user.id:
            raise ValidationError({'detail': 'A project creator cannot donate to their own project.'})

        if not project.is_open_for_donations:
            raise ValidationError({'detail': 'This project is not currently accepting donations.'})

        if is_stripe_configured():
            return self._start_stripe_payment(request, project)

        return self._run_mock_payment(request, project)

    def _start_stripe_payment(self, request, project):
        serializer = DonationStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        idempotency_key = data.get('idempotency_key', '')
        if idempotency_key:
            existing = (
                Donation.objects.filter(idempotency_key=idempotency_key, user=request.user)
                .select_related('project')
                .first()
            )
            if existing:
                if existing.status == Donation.STATUS_SUCCESSFUL:
                    # Already paid on a previous attempt — replay the result.
                    return Response(
                        DonationHistorySerializer(existing, context={'request': request}).data,
                        status=status.HTTP_200_OK,
                    )
                return Response(
                    {'detail': 'A payment attempt with this reference is already in progress.'},
                    status=status.HTTP_409_CONFLICT,
                )

        donation = Donation.objects.create(
            user=request.user,
            project=project,
            amount=data['amount'],
            status=Donation.STATUS_PENDING,
            gateway='stripe',
            currency=data['currency'],
            is_anonymous=data.get('is_anonymous', False),
            cardholder_name=data.get('cardholder_name', ''),
            idempotency_key=idempotency_key,
        )

        try:
            client_secret, intent_id = create_payment_intent(
                amount=data['amount'],
                currency=data['currency'],
                donation_id=donation.id,
                user_id=request.user.id,
            )
        except GatewayError:
            donation.status = Donation.STATUS_FAILED
            donation.failure_reason = 'gateway_unavailable'
            donation.save(update_fields=['status', 'failure_reason'])
            return Response(
                {'detail': 'Payment gateway is unavailable right now. Please try again later.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                'gateway': 'stripe',
                'donation_id': donation.id,
                'payment_intent_id': intent_id,
                'client_secret': client_secret,
            },
            status=status.HTTP_201_CREATED,
        )

    def _run_mock_payment(self, request, project):
        serializer = DonationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Idempotency: a retried request with the same key (e.g. after a
        # timed-out first attempt) returns the already-processed donation
        # instead of charging the card again.
        idempotency_key = data.get('idempotency_key', '')
        if idempotency_key:
            existing = (
                Donation.objects.filter(idempotency_key=idempotency_key, user=request.user)
                .select_related('project')
            ).first()
            if existing:
                return Response(
                    DonationHistorySerializer(existing, context={'request': request}).data,
                    status=status.HTTP_200_OK,
                )

        card_number = digits_only(data['card_number'])
        donation = Donation.objects.create(
            user=request.user,
            project=project,
            amount=data['amount'],
            status=Donation.STATUS_PENDING,
            gateway='mock',
            currency=data['currency'],
            is_anonymous=data.get('is_anonymous', False),
            cardholder_name=data.get('cardholder_name', ''),
            card_last4=card_number[-4:],
            idempotency_key=idempotency_key,
        )

        try:
            result = process_mock_payment(
                amount=data['amount'],
                currency=data['currency'],
                card_number=card_number,
                card_expiry=data['card_expiry'],
                card_cvc=data['card_cvc'],
            )
        except GatewayError:
            donation.status = Donation.STATUS_FAILED
            donation.failure_reason = 'gateway_unavailable'
            donation.save(update_fields=['status', 'failure_reason'])
            return Response(
                {'detail': 'Payment gateway is unavailable right now. Please try again later.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if result.success:
            atomically_raise_fund(project.id, data['amount'])
            donation.status = Donation.STATUS_SUCCESSFUL
            donation.transaction_id = result.transaction_id
            donation.gateway = result.gateway
            donation.failure_reason = ''
            donation.save(update_fields=['status', 'transaction_id', 'gateway', 'failure_reason'])
            return Response(
                DonationHistorySerializer(donation, context={'request': request}).data,
                status=status.HTTP_201_CREATED,
            )

        donation.status = Donation.STATUS_FAILED
        donation.gateway = result.gateway
        donation.failure_reason = result.error_message
        donation.save(update_fields=['status', 'gateway', 'failure_reason'])
        return Response(
            {
                'detail': result.error_message,
                'error_code': result.error_code,
                'donation': DonationHistorySerializer(donation, context={'request': request}).data,
            },
            status=status.HTTP_402_PAYMENT_REQUIRED,
        )


def atomically_raise_fund(project_id, amount):
    """Guaranteed single-statement increment (F()) so two concurrent
    successful payments can never lose a donation to a read-modify-write
    race."""
    Project.objects.filter(pk=project_id).update(current_fund=F('current_fund') + amount)


class MyDonationsView(generics.ListAPIView):
    """GET /api/donations/my-donations/ — PROJECT_SPEC.md 6, 10."""
    serializer_class = DonationHistorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Donation.objects.filter(user=self.request.user)
            .select_related('project')
            .prefetch_related('project__images')
        )

    def get_serializer_context(self):
        return {'request': self.request}


class CategoryListView(generics.ListAPIView):
    """GET /api/categories/"""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None


class CategoryProjectsView(generics.ListAPIView):
    """GET /api/categories/<slug>/projects/ — paginated (PROJECT_SPEC.md 6, 10)."""
    serializer_class = ProjectListSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        category = get_object_or_404(Category, slug=self.kwargs['slug'])
        return _project_queryset().filter(category=category)

    def get_serializer_context(self):
        return {'request': self.request}


class TagListView(generics.ListAPIView):
    """GET /api/tags/"""
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None
