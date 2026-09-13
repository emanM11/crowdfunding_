from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.utils import timezone
from django.utils.text import slugify


class Category(models.Model):
    """PROJECT_SPEC.md 5.2 — managed by admins via Django admin."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True, allow_unicode=True)

    class Meta:
        verbose_name_plural = 'categories'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            # allow_unicode=True — plain slugify() strips non-Latin
            # characters entirely, which would silently turn every Arabic
            # category name into the same empty/duplicate slug.
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Tag(models.Model):
    """PROJECT_SPEC.md 5.3 — free-form tags, many-to-many with Project."""
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Project(models.Model):
    """
    PROJECT_SPEC.md 5.4.

    Status handling: `status` is only ever written to directly for the
    'cancelled' value (see cancel() below). 'running' vs 'ended' is always
    derived from the dates at read time via `computed_status`, so a stalled
    background job can never leave a project stuck in a stale status.

    Note on projects that haven't started yet (start_date > now): the
    3-value contract (running/cancelled/ended) has no separate state for
    this, so `computed_status` reports them as 'running' — they are not
    cancelled or past their end date. Endpoints that specifically need the
    stricter "currently inside its date window" check (the donation
    endpoint, and the homepage top-rated slider) use `is_open_for_donations`
    instead of relying on this field alone.
    """

    STATUS_CHOICES = [
        ('running', 'Running'),
        ('cancelled', 'Cancelled'),
        ('ended', 'Ended'),
    ]

    title = models.CharField(max_length=200)
    details = models.TextField()
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name='projects'
    )
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='projects'
    )
    tags = models.ManyToManyField(Tag, related_name='projects', blank=True)

    total_target = models.DecimalField(max_digits=12, decimal_places=2)
    start_date = models.DateField()
    end_date = models.DateField()

    # Denormalized raised amount for the donate/payment flow — incremented
    # atomically on every gateway-confirmed donation (projects/views.py
    # DonationProcessView). Kept in sync with total_donations() which is the
    # read-time aggregation source of truth (PROJECT_SPEC.md 11).
    current_fund = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Only ever set directly for 'cancelled' — see class docstring.
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='running')
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def computed_status(self):
        if self.status == 'cancelled':
            return 'cancelled'
        if timezone.localdate() > self.end_date:
            return 'ended'
        return 'running'

    @property
    def is_open_for_donations(self):
        """Strict date-window + status check used by the donate endpoint
        and the homepage top-rated slider (PROJECT_SPEC.md 5.4, 5.6)."""
        today = timezone.localdate()
        return (
            self.status != 'cancelled'
            and self.start_date <= today <= self.end_date
        )

    def total_donations(self):
        """Gateway-confirmed money only. Always computed via DB aggregation
        — never looped in Python (PROJECT_SPEC.md 11)."""
        return self.successful_donations().aggregate(total=Sum('amount'))['total'] or 0

    def successful_donations(self):
        """The donations that actually raised money (status='successful').
        pending/failed donations never count toward funding totals, the 25%
        cancellation threshold, or reward backer counts."""
        return self.donations.filter(status=Donation.STATUS_SUCCESSFUL)

    def sync_current_fund(self):
        """Recompute current_fund from successful donations (used by seed
        data and the backfill migration)."""
        self.current_fund = self.total_donations()
        self.save(update_fields=['current_fund'])

    def can_be_cancelled(self):
        """PROJECT_SPEC.md 5.4 cancellation rule: strictly less than 25% of
        target. Exactly 25% does not qualify. Uses Decimal throughout —
        mixing Decimal with a plain float here would raise a TypeError."""
        from decimal import Decimal
        target = self.total_target or Decimal('0')
        if target <= 0:
            return False
        return self.total_donations() < (target * Decimal('0.25'))

    def cancel(self):
        self.status = 'cancelled'
        self.save(update_fields=['status'])

    def similar_projects(self, limit=4):
        """
        PROJECT_SPEC.md 5.4: rank by number of shared tags (desc), running
        projects as a tiebreaker, never more than `limit`, no duplicates,
        excludes self.
        """
        tag_ids = list(self.tags.values_list('id', flat=True))
        if not tag_ids:
            return Project.objects.none()

        candidates = (
            Project.objects.exclude(id=self.id)
            .filter(tags__id__in=tag_ids)
            .distinct()
            .annotate(shared_tags=models.Count('tags', filter=models.Q(tags__id__in=tag_ids)))
        )
        # Running-first tiebreak can't be expressed purely in SQL here
        # without duplicating the date-derived status logic in the DB, so
        # it's applied in Python on an already-small, already-ranked slice.
        candidates = list(candidates.order_by('-shared_tags')[: limit * 3])
        candidates.sort(key=lambda p: (-p.shared_tags, p.computed_status != 'running'))
        return candidates[:limit]


class ProjectImage(models.Model):
    """PROJECT_SPEC.md 5.5 — multiple images per project."""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='project_images/')

    def __str__(self):
        return f'Image for {self.project.title}'


class ProjectUpdate(models.Model):
    """Creator-posted progress notes shown on the project detail page."""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='updates')
    title = models.CharField(max_length=200)
    body = models.TextField()
    image = models.ImageField(upload_to='project_updates/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Update: {self.title} ({self.project.title})'


class RewardTier(models.Model):
    """
    Backer rewards / funding tiers (PROJECT_SPEC.md 5.4 bonus).
    `quantity` is an optional cap; `None` means unlimited.
    """
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='rewards')
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True, default='')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField(blank=True, null=True)
    estimated_delivery = models.CharField(max_length=100, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['amount']

    def __str__(self):
        return f'{self.title} ({self.amount})'


class Donation(models.Model):
    """
    PROJECT_SPEC.md 5.6 — payment-backed donation.

    `amount` is a DecimalField — never FloatField, per the explicit note in
    PROJECT_SPEC.md 16. `status` starts 'pending' and is only flipped to
    'successful' after the payment gateway confirms the charge
    (projects/views.py DonationProcessView); a declined/unfinished payment
    leaves a 'failed' row behind for auditing, but failed/pending rows never
    count toward the project's raised total. Card numbers are never stored —
    only `cardholder_name` and the masked `card_last4`.
    """
    STATUS_PENDING = 'pending'
    STATUS_SUCCESSFUL = 'successful'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_SUCCESSFUL, 'Successful'),
        (STATUS_FAILED, 'Failed'),
    ]
    CURRENCY_CHOICES = [('EGP', 'Egyptian Pound'), ('USD', 'US Dollar')]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='donations'
    )
    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name='donations')
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    # Gateway reference id for auditing (e.g. pi_... from Stripe).
    transaction_id = models.CharField(max_length=128, unique=True, blank=True, null=True)
    # Client-generated key so a retried request can't double-charge.
    # Looked up server-side; not a DB uniqueness constraint.
    idempotency_key = models.CharField(max_length=128, blank=True, default='', db_index=True)
    gateway = models.CharField(max_length=32, default='mock')
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='EGP')
    is_anonymous = models.BooleanField(default=False)
    cardholder_name = models.CharField(max_length=150, blank=True, default='')
    card_last4 = models.CharField(max_length=4, blank=True, default='')  # PCI-safe masked
    card_brand = models.CharField(max_length=32, blank=True, default='')  # e.g. visa / mastercard
    failure_reason = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.amount} by {self.user} on {self.project}'
