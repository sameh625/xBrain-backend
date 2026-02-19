from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    RegisterView,
    VerifyEmailView,
    LoginView,
    ResendOTPView,
    UserProfileView,
    SpecializationListView,
    UserSpecializationView,
)

app_name = 'api'

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/verify-email/', VerifyEmailView.as_view(), name='verify-email'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/resend-otp/', ResendOTPView.as_view(), name='resend-otp'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),

    path('users/me/', UserProfileView.as_view(), name='user-profile'),
    path('users/me/specializations/', UserSpecializationView.as_view(), name='user-specializations'),

    path('specializations/', SpecializationListView.as_view(), name='specializations'),
]
