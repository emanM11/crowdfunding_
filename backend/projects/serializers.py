from rest_framework import serializers

from accounts.serializers import validate_image_size

from .models import (
    Category,
    Donation,
    Project,
    ProjectImage,
    ProjectUpdate,
    RewardTier,
    Tag,
)
from .payments import PaymentError, digits_only, validate_card


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name']


class ProjectImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectImage
        fields = ['id', 'image']


class ProjectCreatorSerializer(serializers.Serializer):
    """Minimal, safe-to-expose creator info — no email/phone leaked here."""
    id = serializers.IntegerField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    bio = serializers.CharField(allow_blank=True, required=False)
    avatar = serializers.SerializerMethodField()

    def get_avatar(self, obj):
        if not getattr(obj, 'profile_picture', None):
            return None
        request = self.context.get('request')
        url = obj.profile_picture.url
        return request.build_absolute_uri(url) if request else url


class ProjectUpdateSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ProjectUpdate
        fields = ['id', 'title', 'body', 'image', 'image_url', 'created_at']
        read_only_fields = ['id', 'created_at']
        extra_kwargs = {'image': {'write_only': True, 'required': False}}

    def get_image_url(self, obj):
        if not obj.image:
            return None
        request = self.context.get('request')
        url = obj.image.url
        return request.build_absolute_uri(url) if request else url


class RewardTierSerializer(serializers.ModelSerializer):
    backers = serializers.SerializerMethodField()

    class Meta:
        model = RewardTier
        fields = [
            'id', 'title', 'description', 'amount', 'quantity',
            'estimated_delivery', 'backers', 'created_at',
        ]

    def get_backers(self, obj):
        # Number of gateway-confirmed donations at or above this tier's
        # amount — pending/failed donations don't count as backers.
        return obj.project.successful_donations().filter(amount__gte=obj.amount).count()


class ProjectListSerializer(serializers.ModelSerializer):
    """Lightweight shape for list/browse endpoints (project list, category
    browsing, search, homepage lists, similar projects)."""
    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    status = serializers.CharField(source='computed_status', read_only=True)
    total_donations = serializers.SerializerMethodField()
    current_fund = serializers.SerializerMethodField()
    thumbnail = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            'id', 'title', 'category', 'tags', 'total_target', 'total_donations',
            'current_fund', 'start_date', 'end_date', 'status', 'is_featured',
            'thumbnail', 'created_at',
        ]

    def get_total_donations(self, obj):
        return str(obj.total_donations())

    def get_current_fund(self, obj):
        return str(obj.current_fund)

    def get_thumbnail(self, obj):
        first_image = obj.images.first()
        if not first_image:
            return None
        request = self.context.get('request')
        url = first_image.image.url
        return request.build_absolute_uri(url) if request else url


class ProjectDetailSerializer(serializers.ModelSerializer):
    """
    Full detail shape — PROJECT_SPEC.md 5.4 / 6.1: all images, average
    rating, rating count, the caller's own rating, and up to 4 similar
    projects.

    average_rating / rating_count / my_rating are wired to real values once
    the `core` app's Rating model exists (build order step 11); until then
    they report safe, well-typed defaults so the field names in the
    contract are stable from day one and the frontend can build against
    them immediately.
    """
    category = CategorySerializer(read_only=True)
    creator = ProjectCreatorSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    images = ProjectImageSerializer(many=True, read_only=True)
    updates = ProjectUpdateSerializer(many=True, read_only=True)
    rewards = RewardTierSerializer(many=True, read_only=True)
    status = serializers.CharField(source='computed_status', read_only=True)
    total_donations = serializers.SerializerMethodField()
    current_fund = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    rating_count = serializers.SerializerMethodField()
    my_rating = serializers.SerializerMethodField()
    similar_projects = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            'id', 'title', 'details', 'category', 'creator', 'tags',
            'total_target', 'total_donations', 'current_fund', 'start_date',
            'end_date', 'status', 'is_featured', 'images', 'updates', 'rewards',
            'average_rating', 'rating_count', 'my_rating',
            'similar_projects', 'created_at',
        ]

    def get_total_donations(self, obj):
        return str(obj.total_donations())

    def get_current_fund(self, obj):
        return str(obj.current_fund)

    def get_average_rating(self, obj):
        if not _has_core_rating():
            return None
        from django.apps import apps
        from django.db.models import Avg
        rating_model = apps.get_model('core', 'Rating')
        return rating_model.objects.filter(project=obj).aggregate(avg=Avg('value'))['avg']

    def get_rating_count(self, obj):
        if not _has_core_rating():
            return 0
        from django.apps import apps
        rating_model = apps.get_model('core', 'Rating')
        return rating_model.objects.filter(project=obj).count()

    def get_my_rating(self, obj):
        request = self.context.get('request')
        if not _has_core_rating() or not request or not request.user.is_authenticated:
            return None
        from django.apps import apps
        rating_model = apps.get_model('core', 'Rating')
        rating = rating_model.objects.filter(project=obj, user=request.user).first()
        return rating.value if rating else None

    def get_similar_projects(self, obj):
        return ProjectListSerializer(
            obj.similar_projects(), many=True, context=self.context
        ).data


def _has_core_rating():
    from django.apps import apps
    try:
        apps.get_model('core', 'Rating')
        return True
    except LookupError:
        return False


class ProjectCreateUpdateSerializer(serializers.ModelSerializer):
    """
    PROJECT_SPEC.md 5.5, 6, 6.1: single multipart request — project fields,
    tags, and all images together. `images` accepts multiple files under
    the same form key; `tags` accepts a list of tag name strings and
    get_or_creates them, so the frontend doesn't need to manage tag IDs.
    """
    images = serializers.ListField(
        child=serializers.ImageField(), write_only=True, required=False
    )
    tags = serializers.ListField(
        child=serializers.CharField(max_length=50), write_only=True, required=False
    )

    class Meta:
        model = Project
        fields = [
            'id', 'title', 'details', 'category', 'tags',
            'total_target', 'start_date', 'end_date', 'images',
        ]

    def validate_images(self, images):
        # Security hardening (PROJECT_SPEC.md 16): same size ceiling as
        # profile pictures, applied to every file in the batch.
        for image in images:
            validate_image_size(image)
        if len(images) > 10:
            raise serializers.ValidationError('You can upload at most 10 images per project.')
        return images

    def validate_total_target(self, value):
        if value <= 0:
            raise serializers.ValidationError('total_target must be greater than zero.')
        return value

    def validate(self, attrs):
        start = attrs.get('start_date', getattr(self.instance, 'start_date', None))
        end = attrs.get('end_date', getattr(self.instance, 'end_date', None))
        if start and end and end <= start:
            raise serializers.ValidationError({'end_date': 'end_date must be after start_date.'})
        return attrs

    def _set_tags(self, project, tag_names):
        tags = [Tag.objects.get_or_create(name=name.strip())[0] for name in tag_names if name.strip()]
        project.tags.set(tags)

    def create(self, validated_data):
        images = validated_data.pop('images', [])
        tag_names = validated_data.pop('tags', [])
        project = Project.objects.create(creator=self.context['request'].user, **validated_data)
        self._set_tags(project, tag_names)
        ProjectImage.objects.bulk_create(
            [ProjectImage(project=project, image=img) for img in images]
        )
        return project

    def update(self, instance, validated_data):
        images = validated_data.pop('images', None)
        tag_names = validated_data.pop('tags', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if tag_names is not None:
            self._set_tags(instance, tag_names)
        if images:
            ProjectImage.objects.bulk_create(
                [ProjectImage(project=instance, image=img) for img in images]
            )
        return instance

    def to_representation(self, instance):
        # Respond with the full detail shape after create/update.
        return ProjectDetailSerializer(instance, context=self.context).data


class DonationCreateSerializer(serializers.Serializer):
    """
    Donation payment request. Card fields are validated server-side as
    defense in depth (PROJECT_SPEC.md 16) and are write_only — the payload
    carries them to the gateway but they never reach any response or model.
    `idempotency_key` is a client-generated key (e.g. crypto.randomUUID())
    so the view can refuse to charge twice on a retried request.
    """
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.ChoiceField(choices=Donation.CURRENCY_CHOICES, default='EGP')
    is_anonymous = serializers.BooleanField(default=False, required=False)
    cardholder_name = serializers.CharField(max_length=150, allow_blank=True, required=False)
    idempotency_key = serializers.CharField(max_length=128, allow_blank=True, required=False)

    card_number = serializers.CharField(write_only=True, max_length=32)
    card_expiry = serializers.CharField(write_only=True, max_length=7, label='Expiry (MM/YY)')
    card_cvc = serializers.CharField(write_only=True, max_length=4)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('amount must be greater than zero.')
        return value

    def validate_cardholder_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('Cardholder name is required.')
        return value.strip()

    def validate(self, attrs):
        try:
            number, _, _ = validate_card(
                attrs['card_number'], attrs['card_expiry'], attrs['card_cvc']
            )
        except PaymentError as exc:
            raise serializers.ValidationError({exc.field: exc.message})
        # Keep only the digits — the view uses them for the masked record and
        # to hand the gateway a clean number.
        attrs['card_number'] = number
        return attrs


class DonationHistorySerializer(serializers.ModelSerializer):
    """PROJECT_SPEC.md 6: project id, project title, project image,
    donation amount, and donation date for each entry, plus the payment
    status / gateway reference so the user can audit their donations."""
    project_id = serializers.IntegerField(source='project.id')
    project_title = serializers.CharField(source='project.title')
    project_image = serializers.SerializerMethodField()
    payment_method = serializers.SerializerMethodField()

    class Meta:
        model = Donation
        fields = [
            'project_id', 'project_title', 'project_image', 'amount',
            'currency', 'status', 'transaction_id', 'is_anonymous',
            'payment_method', 'created_at',
        ]

    def get_project_image(self, obj):
        first_image = obj.project.images.first()
        if not first_image:
            return None
        request = self.context.get('request')
        url = first_image.image.url
        return request.build_absolute_uri(url) if request else url

    def get_payment_method(self, obj):
        # Masked card, e.g. "visa •••• 4242". Full numbers are never stored
        # (PCI). In mock mode only the last-4 arrives (no brand detection).
        if not obj.card_last4:
            return None
        if obj.card_brand:
            return f'{obj.card_brand} •••• {obj.card_last4}'
        return obj.card_last4


class DonationStartSerializer(serializers.Serializer):
    """
    Stripe-mode request: the browser tokenizes the card with Elements, so
    this serializer carries NO card fields — just the donation itself. The
    PaymentIntent is created server-side and the client confirms it.
    """
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.ChoiceField(choices=Donation.CURRENCY_CHOICES, default='EGP')
    is_anonymous = serializers.BooleanField(default=False, required=False)
    cardholder_name = serializers.CharField(max_length=150, allow_blank=True, required=False)
    idempotency_key = serializers.CharField(max_length=128, allow_blank=True, required=False)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('amount must be greater than zero.')
        return value
