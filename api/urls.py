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
    ForgotPasswordView,
    VerifyResetOTPView,
    ResetPasswordView,
)

app_name = 'api'

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/verify-email/', VerifyEmailView.as_view(), name='verify-email'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/resend-otp/', ResendOTPView.as_view(), name='resend-otp'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('auth/forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('auth/verify-reset-otp/', VerifyResetOTPView.as_view(), name='verify-reset-otp'),
    path('auth/reset-password/', ResetPasswordView.as_view(), name='reset-password'),

    path('users/me/', UserProfileView.as_view(), name='user-profile'),
    path('users/me/specializations/', UserSpecializationView.as_view(), name='user-specializations'),

    path('specializations/', SpecializationListView.as_view(), name='specializations'),
]
