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
    QuestionListCreateView,
    QuestionDetailView,
    QuestionResolveView,
    QuestionUnresolveView,
    AnswerListCreateView,
    AnswerDetailView,
    ReplyListCreateView,
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

    # Q&A (Sprint 2)
    path('questions/', QuestionListCreateView.as_view(), name='questions'),
    path('questions/<uuid:pk>/', QuestionDetailView.as_view(), name='question-detail'),
    path('questions/<uuid:pk>/resolve/', QuestionResolveView.as_view(), name='question-resolve'),
    path('questions/<uuid:pk>/unresolve/', QuestionUnresolveView.as_view(), name='question-unresolve'),
    path('questions/<uuid:question_id>/answers/', AnswerListCreateView.as_view(), name='question-answers'),
    path('answers/<uuid:pk>/', AnswerDetailView.as_view(), name='answer-detail'),
    path('answers/<uuid:pk>/replies/', ReplyListCreateView.as_view(), name='answer-replies'),
]
