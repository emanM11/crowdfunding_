from django.urls import path

from .views import (
    CommentListCreateView,
    CommentReplyView,
    HomepageView,
    RateProjectView,
    ReportCreateView,
    SearchView,
)

app_name = 'core'

urlpatterns = [
    path('projects/<int:pk>/comments/', CommentListCreateView.as_view(), name='project-comments'),
    path('comments/<int:pk>/reply/', CommentReplyView.as_view(), name='comment-reply'),
    path('projects/<int:pk>/rate/', RateProjectView.as_view(), name='project-rate'),
    path('reports/', ReportCreateView.as_view(), name='report-create'),
    path('homepage/', HomepageView.as_view(), name='homepage'),
    path('search/', SearchView.as_view(), name='search'),
]
