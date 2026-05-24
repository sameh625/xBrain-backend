from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from drf_spectacular.utils import extend_schema, extend_schema_view

TaggedTokenRefreshView = extend_schema_view(
    post=extend_schema(
        tags=['Auth'],
        operation_id='auth_08_token_refresh',
        summary='Refresh JWT tokens',
        description='Exchanges a refresh token for a new access + refresh token pair. The old refresh token is blacklisted.',
    )
)(TokenRefreshView)

from .views import (
    RegisterView,
    VerifyEmailView,
    LoginView,
    ResendOTPView,
    LogoutView,
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
    AttachmentDeleteView,
    PostListCreateView,
    PostDetailView,
    PostLikeView,
    PostDislikeView,
    MyCertificatesListCreateView,
    MyCertificateDeleteView,
    UserCertificatesPublicView,
    CommentListCreateView,
    CommentDetailView,
    CommentReplyListCreateView,
    MyPostsListView,
    MyQuestionsListView,
    UserPostsListView,
    UserQuestionsListView,
    UserProfileDetailView,
    UserPublicSpecializationsView,
    RequestMeetingView,
    AcceptMeetingView,
    DeclineMeetingView,
    CancelMeetingView,
    MyOutgoingMeetingRequestsView,
    MyIncomingMeetingRequestsView,
    MeetingRequestDetailView,
)

app_name = 'api'

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/verify-email/', VerifyEmailView.as_view(), name='verify-email'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/resend-otp/', ResendOTPView.as_view(), name='resend-otp'),
    path('auth/token/refresh/', TaggedTokenRefreshView.as_view(), name='token-refresh'),
    path('auth/forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('auth/verify-reset-otp/', VerifyResetOTPView.as_view(), name='verify-reset-otp'),
    path('auth/reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),

    path('users/me/', UserProfileView.as_view(), name='user-profile'),
    path('users/me/specializations/', UserSpecializationView.as_view(), name='user-specializations'),

    path('specializations/', SpecializationListView.as_view(), name='specializations'),

    path('questions/', QuestionListCreateView.as_view(), name='questions'),
    path('questions/<uuid:pk>/', QuestionDetailView.as_view(), name='question-detail'),
    path('questions/<uuid:pk>/resolve/', QuestionResolveView.as_view(), name='question-resolve'),
    path('questions/<uuid:pk>/unresolve/', QuestionUnresolveView.as_view(), name='question-unresolve'),
    path('questions/<uuid:question_id>/answers/', AnswerListCreateView.as_view(), name='question-answers'),
    path('answers/<uuid:pk>/', AnswerDetailView.as_view(), name='answer-detail'),
    path('answers/<uuid:pk>/replies/', ReplyListCreateView.as_view(), name='answer-replies'),

    path('attachments/<uuid:pk>/', AttachmentDeleteView.as_view(), name='attachment-delete'),

    path('posts/', PostListCreateView.as_view(), name='posts'),
    path('posts/<uuid:pk>/', PostDetailView.as_view(), name='post-detail'),
    path('posts/<uuid:pk>/like/', PostLikeView.as_view(), name='post-like'),
    path('posts/<uuid:pk>/dislike/', PostDislikeView.as_view(), name='post-dislike'),

    # Certificates (Sprint 2 — Item 4)
    path('users/me/certificates/', MyCertificatesListCreateView.as_view(), name='my-certificates'),
    path('users/me/certificates/<uuid:pk>/', MyCertificateDeleteView.as_view(), name='my-certificate-delete'),
    path('users/<uuid:user_id>/certificates/', UserCertificatesPublicView.as_view(), name='user-certificates'),

    # Comments + replies on Posts (Sprint 2 — Item 3)
    path('posts/<uuid:post_id>/comments/', CommentListCreateView.as_view(), name='post-comments'),
    path('comments/<uuid:pk>/', CommentDetailView.as_view(), name='comment-detail'),
    path('comments/<uuid:pk>/replies/', CommentReplyListCreateView.as_view(), name='comment-replies'),

    # User-scoped feeds: my posts/questions, other users' posts/questions, public profile
    path('users/me/posts/', MyPostsListView.as_view(), name='my-posts'),
    path('users/me/questions/', MyQuestionsListView.as_view(), name='my-questions'),
    path('users/<uuid:user_id>/', UserProfileDetailView.as_view(), name='user-profile-public'),
    path('users/<uuid:user_id>/posts/', UserPostsListView.as_view(), name='user-posts'),
    path('users/<uuid:user_id>/questions/', UserQuestionsListView.as_view(), name='user-questions'),
    path('users/<uuid:user_id>/specializations/', UserPublicSpecializationsView.as_view(), name='user-specializations-public'),

    # Meetings: Google Meet on Q&A answers
    path('answers/<uuid:pk>/request-meeting/', RequestMeetingView.as_view(), name='request-meeting'),
    path('meeting-requests/<uuid:pk>/accept/', AcceptMeetingView.as_view(), name='accept-meeting'),
    path('meeting-requests/<uuid:pk>/decline/', DeclineMeetingView.as_view(), name='decline-meeting'),
    path('meeting-requests/<uuid:pk>/cancel/', CancelMeetingView.as_view(), name='cancel-meeting'),
    path('users/me/meeting-requests/outgoing/', MyOutgoingMeetingRequestsView.as_view(), name='my-meetings-outgoing'),
    path('users/me/meeting-requests/incoming/', MyIncomingMeetingRequestsView.as_view(), name='my-meetings-incoming'),
    path('meeting-requests/<uuid:pk>/', MeetingRequestDetailView.as_view(), name='meeting-request-detail'),
]
