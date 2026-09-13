from django.urls import path

from .payment_views import (
    DonationConfirmView,
    PaymentConfigView,
    PaymentWebhookView,
)
from .views import (
    CategoryListView,
    CategoryProjectsView,
    DonationProcessView,
    MyDonationsView,
    MyProjectsView,
    ProjectCancelView,
    ProjectDetailView,
    ProjectListCreateView,
    ProjectUpdateListCreateView,
    RewardTierListCreateView,
    TagListView,
)

app_name = 'projects'

urlpatterns = [
    path('projects/', ProjectListCreateView.as_view(), name='project-list-create'),
    path('projects/my-projects/', MyProjectsView.as_view(), name='my-projects'),
    path('projects/<int:pk>/', ProjectDetailView.as_view(), name='project-detail'),
    path('projects/<int:pk>/cancel/', ProjectCancelView.as_view(), name='project-cancel'),
    path('projects/<int:pk>/donate/process/', DonationProcessView.as_view(), name='project-donate-process'),
    path('projects/<int:pk>/donate/confirm/', DonationConfirmView.as_view(), name='project-donate-confirm'),
    path('projects/<int:pk>/donate/', DonationProcessView.as_view(), name='project-donate'),
    path('projects/<int:pk>/updates/', ProjectUpdateListCreateView.as_view(), name='project-updates'),
    path('projects/<int:pk>/rewards/', RewardTierListCreateView.as_view(), name='project-rewards'),
    path('donations/my-donations/', MyDonationsView.as_view(), name='my-donations'),
    path('payments/config/', PaymentConfigView.as_view(), name='payment-config'),
    path('payments/webhook/', PaymentWebhookView.as_view(), name='payment-webhook'),
    path('categories/', CategoryListView.as_view(), name='category-list'),
    path('categories/<str:slug>/projects/', CategoryProjectsView.as_view(), name='category-projects'),
    path('tags/', TagListView.as_view(), name='tag-list'),
]
