from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    ActivateView,
    FacebookLoginView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    ProfileView,
    RegisterView,
    ThrottledTokenObtainPairView,
)

app_name = 'accounts'

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('activate/<int:uid>/<str:token>/', ActivateView.as_view(), name='activate'),
    path('token/', ThrottledTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('password-reset/', PasswordResetRequestView.as_view(), name='password-reset'),
    path('password-reset/confirm/<int:uid>/<str:token>/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('facebook/', FacebookLoginView.as_view(), name='facebook-login'),
]
