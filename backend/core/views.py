from django.db.models import Avg, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from projects.models import Category, Donation, Project
from projects.serializers import CategorySerializer, ProjectListSerializer
from projects.views import _project_queryset

from .models import Comment, Rating
from .serializers import (
    CommentCreateSerializer,
    CommentSerializer,
    ReplyCreateSerializer,
    ReportSerializer,
    RatingSerializer,
)


class CommentListCreateView(generics.ListCreateAPIView):
    """GET/POST /api/projects/<id>/comments/ — PROJECT_SPEC.md 5.7, 6."""
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_project(self):
        return get_object_or_404(Project, pk=self.kwargs['pk'])

    def get_queryset(self):
        return (
            Comment.objects.filter(project_id=self.kwargs['pk'], parent__isnull=True)
            .select_related('user')
            .prefetch_related('replies__user')
        )

    def get_serializer_class(self):
        return CommentCreateSerializer if self.request.method == 'POST' else CommentSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.request.method == 'POST':
            context['project'] = self.get_project()
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = serializer.save()
        return Response(CommentSerializer(comment).data, status=status.HTTP_201_CREATED)


class CommentReplyView(APIView):
    """POST /api/comments/<id>/reply/ — bonus (PROJECT_SPEC.md 5.7)."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        parent = get_object_or_404(Comment, pk=pk)
        if parent.parent_id is not None:
            raise ValidationError({'detail': 'Cannot reply to a reply — only top-level comments accept replies.'})
        serializer = ReplyCreateSerializer(data=request.data, context={'request': request, 'parent': parent})
        serializer.is_valid(raise_exception=True)
        reply = serializer.save()
        from .serializers import ReplySerializer
        return Response(ReplySerializer(reply).data, status=status.HTTP_201_CREATED)


class RateProjectView(APIView):
    """
    POST /api/projects/<id>/rate/ — PROJECT_SPEC.md 5.8, 6.
    Upsert: a second rating from the same user replaces their first one
    instead of erroring, since "users rate the project" implies one current
    opinion per user, not a permanent history of every rating they've given.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        serializer = RatingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        rating, _created = Rating.objects.update_or_create(
            user=request.user, project=project,
            defaults={'value': serializer.validated_data['value']},
        )
        avg = Rating.objects.filter(project=project).aggregate(avg=Avg('value'))['avg']
        count = Rating.objects.filter(project=project).count()
        return Response(
            {'value': rating.value, 'average_rating': avg, 'rating_count': count},
            status=status.HTTP_200_OK,
        )


class ReportCreateView(generics.CreateAPIView):
    """POST /api/reports/ — reports a project OR a comment, never both
    (PROJECT_SPEC.md 5.9, 6)."""
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


def _running_projects_queryset():
    """PROJECT_SPEC.md 3, 5.4: DB-level equivalent of
    Project.is_open_for_donations, used where we need to filter/order in
    SQL rather than in Python (the homepage top-rated slider)."""
    today = timezone.localdate()
    return _project_queryset().filter(
        Q(start_date__lte=today) & Q(end_date__gte=today) & ~Q(status='cancelled')
    )


class HomepageView(APIView):
    """
    GET /api/homepage/ — PROJECT_SPEC.md 3, 6.
    - top_rated: up to 5 highest-rated running projects
    - latest: latest 5 projects (any status)
    - featured: latest 5 admin-featured projects
    - categories: full category list
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        # _project_queryset() (PROJECT_SPEC.md 11) select/prefetch-relates
        # category, tags and images on every branch here, so serializing
        # three separate 5-item lists costs a handful of queries total
        # instead of one query per project per relation.
        top_rated = (
            _running_projects_queryset()
            .annotate(avg_rating=Avg('ratings__value'))
            .filter(avg_rating__isnull=False)
            .order_by('-avg_rating', '-created_at')[:5]
        )
        latest = _project_queryset().order_by('-created_at')[:5]
        featured = _project_queryset().filter(is_featured=True).order_by('-created_at')[:5]
        categories = Category.objects.all()

        # Site-wide statistics for the homepage stats band — aggregated in
        # SQL (PROJECT_SPEC.md 11), never looped in Python. Only
        # gateway-confirmed donations count toward money raised / backers.
        successful_donations = Donation.objects.filter(status=Donation.STATUS_SUCCESSFUL)
        donations_agg = successful_donations.aggregate(total=Sum('amount'))
        stats = {
            'projects': Project.objects.count(),
            'total_raised': str(donations_agg['total'] or 0),
            'backers': successful_donations.values('user').distinct().count(),
            'categories': categories.count(),
        }

        context = {'request': request}
        return Response({
            'top_rated': ProjectListSerializer(top_rated, many=True, context=context).data,
            'latest': ProjectListSerializer(latest, many=True, context=context).data,
            'featured': ProjectListSerializer(featured, many=True, context=context).data,
            'categories': CategorySerializer(categories, many=True).data,
            'stats': stats,
        })


class SearchView(generics.ListAPIView):
    """GET /api/search/?q=... — PROJECT_SPEC.md 3, 6. Matches project title
    or tag name, case-insensitive, deduplicated, paginated."""
    serializer_class = ProjectListSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        q = self.request.query_params.get('q', '').strip()
        if not q:
            return Project.objects.none()
        return (
            _project_queryset()
            .filter(Q(title__icontains=q) | Q(tags__name__icontains=q))
            .distinct()
            .order_by('-created_at')
        )

    def get_serializer_context(self):
        return {'request': self.request}
