from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.exceptions import ValidationError as DRFValidationError, PermissionDenied
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.contrib.auth import authenticate
from django.db import transaction
from django.db.models import Count, Q, OuterRef, Subquery, CharField
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .serializers import (
    UserRegistrationSerializer,
    VerifyOTPSerializer,
    UserLoginSerializer,
    ResendOTPSerializer,
    UserDetailSerializer,
    UpdateProfileSerializer,
    SpecializationSerializer,
    UserSpecializationSerializer,
    ForgotPasswordSerializer,
    VerifyResetOTPSerializer,
    ResetPasswordSerializer,
    QuestionListSerializer,
    QuestionDetailSerializer,
    QuestionCreateUpdateSerializer,
    AnswerSerializer,
    AnswerCreateSerializer,
    AnswerUpdateSerializer,
    PostListSerializer,
    PostDetailSerializer,
    PostCreateUpdateSerializer,
)
from .models import (
    User, Specialization, UserSpecialization,
    Question, Answer, Post, PostReaction,
)
from .permissions import IsAuthorOrReadOnly, IsQuestionAuthor


class RegisterView(APIView):
    permission_classes = [AllowAny]
    
    @extend_schema(
        tags=['Auth'],
        operation_id='auth_01_register',
        summary="Register a new user",
        description="Creates a pending registration and sends a 6-digit OTP to the provided email.",
        request=UserRegistrationSerializer,
        responses={
            200: OpenApiResponse(description="OTP sent successfully"),
            400: OpenApiResponse(description="Validation error (e.g., email taken, weak password)")
        }
    )
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        
        if serializer.is_valid():
            result = serializer.save()
            return Response(
                {
                    "message": "OTP sent successfully. Please check your email for verification code.",
                    "email": result['email']
                },
                status=status.HTTP_200_OK
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]
    
    @extend_schema(
        tags=['Auth'],
        operation_id='auth_02_verify_email',
        summary="Verify email with OTP",
        description="Verifies the 6-digit OTP sent to the user's email. On success, creates the user account and returns JWT tokens along with the user profile.",
        request=VerifyOTPSerializer,
        responses={
            201: OpenApiResponse(description="Email verified successfully, returning JWT tokens and user profile"),
            400: OpenApiResponse(description="Invalid or expired OTP")
        }
    )
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            
            user_serializer = UserDetailSerializer(user, context={'request': request})
            
            return Response(
                {
                    "message": "Email verified successfully. Welcome to xBrain!",
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "user": user_serializer.data
                },
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = [AllowAny]
    
    @extend_schema(
        tags=['Auth'],
        operation_id='auth_04_login',
        summary="Login user",
        description="Authenticates a user via email or username and password. Returns JWT tokens and the user profile. Implements account lockout after 5 failed attempts.",
        request=UserLoginSerializer,
        responses={
            200: OpenApiResponse(description="Login successful, returning JWT tokens and user profile"),
            400: OpenApiResponse(description="Invalid credentials or account locked")
        }
    )
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            
            user_serializer = UserDetailSerializer(user, context={'request': request})
            
            return Response(
                {
                    "message": "Login successful",
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "user": user_serializer.data
                },
                status=status.HTTP_200_OK
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ResendOTPView(APIView):
    permission_classes = [AllowAny]
    
    @extend_schema(
        tags=['Auth'],
        operation_id='auth_03_resend_otp',
        summary="Resend registration OTP",
        description="Resends the 6-digit OTP to the email of a pending registration. Subject to a 60-second cooldown and a maximum of 3 attempts.",
        request=ResendOTPSerializer,
        responses={
            200: OpenApiResponse(description="OTP resent successfully"),
            400: OpenApiResponse(description="No pending registration found, cooldown active, or max attempts reached")
        }
    )
    def post(self, request):
        serializer = ResendOTPSerializer(data=request.data)
        
        if serializer.is_valid():
            result = serializer.save()
            return Response(
                {
                    "message": "OTP resent successfully. Please check your email.",
                    "email": result['email']
                },
                status=status.HTTP_200_OK
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @extend_schema(
        tags=['Users'],
        operation_id='users_01_me_get',
        summary="Get current user profile",
        description="Returns the profile details of the authenticated user, including their specializations and wallet balance.",
        responses={200: UserDetailSerializer}
    )
    def get(self, request):
        serializer = UserDetailSerializer(request.user, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=['Users'],
        operation_id='users_02_me_update',
        summary="Update current user profile",
        description=(
            "Updates the authenticated user's profile fields. All fields are optional — "
            "only send the fields you want to update. "
            "Use application/json for text-only updates, or multipart/form-data when uploading a profile image."
        ),
        request={
            'application/json': UpdateProfileSerializer,
            'multipart/form-data': UpdateProfileSerializer,
        },
        responses={
            200: UserDetailSerializer,
            400: OpenApiResponse(description="Validation error")
        }
    )
    def patch(self, request):
        serializer = UpdateProfileSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            user_serializer = UserDetailSerializer(request.user, context={'request': request})
            return Response(user_serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SpecializationListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Specializations'],
        operation_id='specializations_01_list',
        summary="List all specializations",
        description="Returns a list of all available specializations in the system.",
        responses={
            200: OpenApiResponse(description="List of specializations or an empty response if none exist")
        }
    )
    def get(self, request):
        specializations = Specialization.objects.all()
        serializer = SpecializationSerializer(specializations, many=True)

        if not specializations.exists():
            return Response(
                {
                    "message": "No specializations are currently available in the system.",
                    "results": []
                },
                status=status.HTTP_200_OK
            )

        return Response(
            {
                "count": specializations.count(),
                "results": serializer.data
            },
            status=status.HTTP_200_OK
        )


class UserSpecializationView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Users'],
        operation_id='users_03_my_specializations_get',
        summary="Get user's specializations",
        description="Returns the specializations currently selected by the authenticated user, along with the timestamp of when they completed the selection form.",
        responses={200: OpenApiResponse(description="User's specializations and form completion status")}
    )
    def get(self, request):
        user = request.user
        specializations = user.specializations.all()
        specialization_data = SpecializationSerializer(specializations, many=True).data

        return Response(
            {
                "specialization_form_completed_at": user.specialization_form_completed_at,
                "specializations": specialization_data
            },
            status=status.HTTP_200_OK
        )

    @extend_schema(
        tags=['Users'],
        operation_id='users_04_my_specializations_set',
        summary="Set user's specializations",
        description="Overwrites the user's current specializations with the provided list of specialization UUIDs. Also marks the specialization form as completed.",
        request=UserSpecializationSerializer,
        responses={
            200: OpenApiResponse(description="Specializations updated successfully"),
            400: OpenApiResponse(description="Invalid specialization IDs provided")
        }
    )
    def put(self, request):
        serializer = UserSpecializationSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        specialization_ids = list(set(serializer.validated_data.get('specialization_ids', [])))

        UserSpecialization.objects.filter(user=user).delete()

        for spec_id in specialization_ids:
            UserSpecialization.objects.create(
                user=user,
                specialization_id=spec_id
            )

        from django.utils import timezone
        user.specialization_form_completed_at = timezone.now()
        user.save(update_fields=['specialization_form_completed_at'])

        specializations = user.specializations.all()
        specialization_data = SpecializationSerializer(specializations, many=True).data

        return Response(
            {
                "specialization_form_completed_at": user.specialization_form_completed_at,
                "specializations": specialization_data
            },
            status=status.HTTP_200_OK
        )

    @extend_schema(
        tags=['Users'],
        operation_id='users_05_my_specializations_skip',
        summary="Skip specialization selection",
        description="Allows the user to skip selecting specializations. Marks the specialization form as completed but assigns no specializations.",
        request=UserSpecializationSerializer,
        responses={
            200: OpenApiResponse(description="Form skipped successfully"),
            400: OpenApiResponse(description="Missing 'skip' boolean in request")
        }
    )
    def patch(self, request):
        serializer = UserSpecializationSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = request.user

        if not serializer.validated_data.get('skip'):
            return Response(
                {"error": "Set 'skip' to true to skip the specialization form."},
                status=status.HTTP_400_BAD_REQUEST
            )

        from django.utils import timezone
        user.specialization_form_completed_at = timezone.now()
        user.save(update_fields=['specialization_form_completed_at'])

        return Response(
            {
                "specialization_form_completed_at": user.specialization_form_completed_at,
                "specializations": []
            },
            status=status.HTTP_200_OK
        )


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]
    
    @extend_schema(
        tags=['Auth'],
        operation_id='auth_05_forgot_password',
        summary="Send password reset OTP",
        description="Generates a 6-digit OTP and sends it to the given user's email address.",
        request=ForgotPasswordSerializer,
        responses={
            200: OpenApiResponse(description="Password reset code sent to your email"),
            400: OpenApiResponse(description="User with this email not found")
        }
    )
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if serializer.is_valid():
            result = serializer.save()
            return Response(result, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyResetOTPView(APIView):
    permission_classes = [AllowAny]
    
    @extend_schema(
        tags=['Auth'],
        operation_id='auth_06_verify_reset_otp',
        summary="Verify password reset OTP",
        description="Validates the OTP sent to the user's email. Returns a secure 15-minute `reset_token` that must be used in the final reset password step.",
        request=VerifyResetOTPSerializer,
        responses={
            200: OpenApiResponse(description="OTP verified, returning `reset_token`"),
            400: OpenApiResponse(description="Invalid or expired OTP code")
        }
    )
    def post(self, request):
        serializer = VerifyResetOTPSerializer(data=request.data)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]
    
    @extend_schema(
        tags=['Auth'],
        operation_id='auth_07_reset_password',
        summary="Reset password",
        description="Sets a new password for the user, using the `reset_token` obtained from the OTP verification step.",
        request=ResetPasswordSerializer,
        responses={
            200: OpenApiResponse(description="Password reset successfully"),
            400: OpenApiResponse(description="Invalid token or weak password")
        }
    )
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            result = serializer.save()
            return Response(result, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    """POST /api/auth/logout/ — blacklists the provided refresh token."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Auth'],
        operation_id='auth_09_logout',
        summary='Logout (blacklist refresh token)',
        description=(
            "Blacklists the provided refresh token so it cannot be used to obtain "
            "new access tokens. The Flutter client should also clear both tokens "
            "from secure storage."
        ),
        request={
            'application/json': {
                'type': 'object',
                'properties': {'refresh': {'type': 'string', 'description': 'The refresh token to blacklist.'}},
                'required': ['refresh'],
            }
        },
        responses={
            205: OpenApiResponse(description='Logged out successfully (refresh token blacklisted).'),
            400: OpenApiResponse(description='Missing or invalid refresh token.'),
            401: OpenApiResponse(description='Authentication required.'),
        },
    )
    def post(self, request):
        refresh = request.data.get('refresh')
        if not refresh:
            return Response(
                {'refresh': ['This field is required.']},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            RefreshToken(refresh).blacklist()
        except Exception:
            return Response(
                {'refresh': ['Invalid or expired refresh token.']},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_205_RESET_CONTENT)


def _question_queryset_with_counts():
    """Annotated queryset used by both list and detail to avoid N+1 on counts.

    `answers_count` is a Facebook-style total: counts top-level answers PLUS replies.
    Same shape as "X comments" on a social media post."""
    return (
        Question.objects
        .select_related('author')
        .prefetch_related('specializations', 'attachments')
        .annotate(
            answers_count=Count('answers', distinct=True),
        )
    )

def _answer_queryset_with_counts():
    return (
        Answer.objects
        .select_related('author', 'question')
        .prefetch_related('attachments')
        .annotate(replies_count=Count('replies'))
    )


class QuestionListCreateView(generics.ListCreateAPIView):
    """GET /api/questions/ — paginated newest-first list.
    POST /api/questions/ — create a question (auth required). Accepts JSON
    or multipart/form-data; in the multipart case, optional file `attachments`
    are stored alongside the question."""
    permission_classes = [IsAuthenticatedOrReadOnly]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return QuestionCreateUpdateSerializer
        return QuestionListSerializer

    def get_queryset(self):
        qs = _question_queryset_with_counts().order_by('-created_at')
        params = self.request.query_params

        author = params.get('author')
        if author:
            qs = qs.filter(author_id=author)

        specialization = params.get('specialization')
        if specialization:
            qs = qs.filter(specializations__id=specialization).distinct()

        is_resolved = params.get('is_resolved')
        if is_resolved is not None:
            if is_resolved.lower() in ('true', '1'):
                qs = qs.filter(is_resolved=True)
            elif is_resolved.lower() in ('false', '0'):
                qs = qs.filter(is_resolved=False)

        q = params.get('q')
        if q:
            qs = qs.filter(content__icontains=q)

        return qs

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @extend_schema(
        tags=['Q&A'],
        operation_id='qa_01_questions_list',
        summary="List questions",
        description="Paginated newest-first list of questions. Filters: ?author=, ?specialization=, ?is_resolved=, ?q=.",
        responses={200: QuestionListSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=['Q&A'],
        operation_id='qa_02_question_create',
        summary="Create a question",
        description="Authenticated users only. Requires content (1–5000 chars) and 1–3 specialization UUIDs.",
        request=QuestionCreateUpdateSerializer,
        responses={
            201: QuestionDetailSerializer,
            400: OpenApiResponse(description="Validation error (e.g., zero or >3 specs, empty content)."),
            401: OpenApiResponse(description="Authentication required."),
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        question = serializer.save(author=request.user)

        question = _question_queryset_with_counts().get(pk=question.pk)
        return Response(
            QuestionDetailSerializer(question, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


class QuestionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET / PATCH / DELETE /api/questions/{id}/."""
    permission_classes = [IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        return _question_queryset_with_counts()

    def get_serializer_class(self):
        if self.request.method in ('PATCH', 'PUT'):
            return QuestionCreateUpdateSerializer
        return QuestionDetailSerializer

    def update(self, request, *args, **kwargs):
        # After update, return the detail shape (with annotations) instead of the create/update shape.
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        instance = self.get_queryset().get(pk=instance.pk)
        return Response(QuestionDetailSerializer(instance, context={'request': request}).data)

    @extend_schema(
        tags=['Q&A'],
        operation_id='qa_03_question_detail',
        summary="Get a question with its first 10 answers (and 2 replies each).",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=['Q&A'],
        operation_id='qa_04_question_update',
        summary="Update a question (author only)",
        request=QuestionCreateUpdateSerializer,
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(
        tags=['Q&A'],
        operation_id='qa_05_question_delete',
        summary="Delete a question (author only). Cascades to answers and replies.",
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


class QuestionResolveView(APIView):
    """POST /api/questions/{id}/resolve/ — asker only. Idempotent."""
    permission_classes = [IsAuthenticated, IsQuestionAuthor]

    @extend_schema(
        tags=['Q&A'],
        operation_id='qa_06_question_resolve',
        summary="Mark a question as resolved (asker only). Idempotent.",
        responses={
            200: QuestionDetailSerializer,
            403: OpenApiResponse(description="Only the question's author may resolve it."),
            404: OpenApiResponse(description="Question not found."),
        },
        request=None,
    )
    def post(self, request, pk):
        question = get_object_or_404(Question, pk=pk)
        self.check_object_permissions(request, question)

        if not question.is_resolved:
            with transaction.atomic():
                question.is_resolved = True
                question.resolved_at = timezone.now()
                question.save(update_fields=['is_resolved', 'resolved_at', 'updated_at'])

        question = _question_queryset_with_counts().get(pk=pk)
        return Response(
            QuestionDetailSerializer(question, context={'request': request}).data,
            status=status.HTTP_200_OK,
        )


class QuestionUnresolveView(APIView):
    """POST /api/questions/{id}/unresolve/ — asker only. Idempotent."""
    permission_classes = [IsAuthenticated, IsQuestionAuthor]

    @extend_schema(
        tags=['Q&A'],
        operation_id='qa_07_question_unresolve',
        summary="Mark a resolved question as unresolved (asker only). Idempotent.",
        responses={
            200: QuestionDetailSerializer,
            403: OpenApiResponse(description="Only the question's author may unresolve it."),
            404: OpenApiResponse(description="Question not found."),
        },
        request=None,
    )
    def post(self, request, pk):
        question = get_object_or_404(Question, pk=pk)
        self.check_object_permissions(request, question)

        if question.is_resolved:
            with transaction.atomic():
                question.is_resolved = False
                question.resolved_at = None
                question.save(update_fields=['is_resolved', 'resolved_at', 'updated_at'])

        question = _question_queryset_with_counts().get(pk=pk)
        return Response(
            QuestionDetailSerializer(question, context={'request': request}).data,
            status=status.HTTP_200_OK,
        )



class AnswerListCreateView(generics.ListCreateAPIView):
    """GET /api/questions/{question_id}/answers/ — list top-level answers under a question.
    POST same URL — create a top-level answer. Accepts JSON or multipart/form-data
    with optional file `attachments`."""
    permission_classes = [IsAuthenticatedOrReadOnly]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return AnswerCreateSerializer
        return AnswerSerializer

    def get_queryset(self):
        question_id = self.kwargs['question_id']
        get_object_or_404(Question, pk=question_id)
        return (
            _answer_queryset_with_counts()
            .filter(question_id=question_id, parent_answer__isnull=True)
            .order_by('created_at')
        )

    def create(self, request, *args, **kwargs):
        question = get_object_or_404(Question, pk=self.kwargs['question_id'])
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        answer = serializer.save(
            author=request.user,
            question=question,
            parent_answer=None,
        )
        answer = _answer_queryset_with_counts().get(pk=answer.pk)
        return Response(
            AnswerSerializer(answer, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        tags=['Q&A'],
        operation_id='qa_08_answers_list',
        summary="List top-level answers for a question.",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=['Q&A'],
        operation_id='qa_09_answer_create',
        summary="Post a top-level answer to a question.",
        request=AnswerCreateSerializer,
        responses={201: AnswerSerializer, 401: OpenApiResponse(description="Authentication required."), 404: OpenApiResponse(description="Question not found.")},
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

class AnswerDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET / PATCH / DELETE /api/answers/{id}/ — works for both top-level answers and replies."""
    permission_classes = [IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        return _answer_queryset_with_counts()

    def get_serializer_class(self):
        if self.request.method in ('PATCH', 'PUT'):
            return AnswerUpdateSerializer
        return AnswerSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        instance = self.get_queryset().get(pk=instance.pk)
        return Response(AnswerSerializer(instance, context={'request': request}).data)

    @extend_schema(
        tags=['Q&A'],
        operation_id='qa_10_answer_detail',
        summary="Get a single answer or reply.",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=['Q&A'],
        operation_id='qa_11_answer_update',
        summary="Update an answer or reply (author only). Only content can be edited.",
        request=AnswerUpdateSerializer,
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(
        tags=['Q&A'],
        operation_id='qa_12_answer_delete',
        summary="Delete an answer or reply (author only). Deleting a top-level answer cascades to replies.",
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


class AttachmentDeleteView(APIView):
    """DELETE /api/attachments/{id}/ — author of the parent only.

    The parent is the Question, Answer, or Reply that owns this attachment.
    Removes both the database row and the file from Azure Blob storage."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Q&A'],
        operation_id='qa_15_attachment_delete',
        summary="Delete an attachment from a Question, Answer, or Reply (parent author only).",
        description=(
            "Removes a single attachment by id. Only the author of the parent "
            "Question/Answer/Reply may delete its attachments. The underlying "
            "file is removed from Azure Blob storage as part of this operation."
        ),
        responses={
            204: OpenApiResponse(description="Attachment deleted."),
            403: OpenApiResponse(description="Only the parent's author may delete its attachments."),
            404: OpenApiResponse(description="Attachment not found."),
        },
        request=None,
    )
    def delete(self, request, pk):
        from .models import Attachment
        attachment = get_object_or_404(Attachment, pk=pk)
        parent = attachment.parent
        if parent is None or getattr(parent, 'author_id', None) != request.user.id:
            raise PermissionDenied("Only the parent's author can delete this attachment.")
        if attachment.file:
            attachment.file.delete(save=False)
        attachment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ReplyListCreateView(generics.ListCreateAPIView):
    """GET /api/answers/{id}/replies/ — list replies under a top-level answer.
    POST same URL — post a reply to that answer (depth-1). Accepts JSON
    or multipart/form-data with optional file `attachments`."""
    permission_classes = [IsAuthenticatedOrReadOnly]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return AnswerCreateSerializer
        return AnswerSerializer

    def get_queryset(self):
        parent_id = self.kwargs['pk']
        get_object_or_404(Answer, pk=parent_id)
        return (
            _answer_queryset_with_counts()
            .filter(parent_answer_id=parent_id)
            .order_by('created_at')
        )

    def create(self, request, *args, **kwargs):
        parent = get_object_or_404(Answer, pk=self.kwargs['pk'])

        if parent.parent_answer_id is not None:
            raise DRFValidationError(
                {"parent_answer": "Replies cannot have replies — depth limit is 1."}
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reply = serializer.save(
            author=request.user,
            question=parent.question,
            parent_answer=parent,
        )
        reply = _answer_queryset_with_counts().get(pk=reply.pk)
        return Response(
            AnswerSerializer(reply, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        tags=['Q&A'],
        operation_id='qa_13_replies_list',
        summary="List replies under a specific answer.",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=['Q&A'],
        operation_id='qa_14_reply_create',
        summary="Post a reply to a specific answer.",
        description="The parent must be a top-level answer (depth-1 threading). Replying to a reply returns 400.",
        request=AnswerCreateSerializer,
        responses={
            201: AnswerSerializer,
            400: OpenApiResponse(description="Cannot reply to a reply (depth-1 limit)."),
            401: OpenApiResponse(description="Authentication required."),
            404: OpenApiResponse(description="Parent answer not found."),
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

def _post_queryset_with_counts(viewer=None):
    """Annotated Post queryset.

    `likes_count` and `dislikes_count` are computed in SQL (default 0 for new
    posts with no reactions yet). `my_reaction` is per-viewer — populated only
    when the viewer is authenticated; otherwise null."""
    qs = (
        Post.objects
        .select_related('author')
        .prefetch_related('specializations', 'attachments')
        .annotate(
            likes_count=Count(
                'reactions',
                filter=Q(reactions__reaction='like'),
                distinct=True,
            ),
            dislikes_count=Count(
                'reactions',
                filter=Q(reactions__reaction='dislike'),
                distinct=True,
            ),
        )
    )
    if viewer is not None and getattr(viewer, 'is_authenticated', False):
        my = (
            PostReaction.objects
            .filter(post=OuterRef('pk'), user=viewer)
            .values('reaction')[:1]
        )
        qs = qs.annotate(my_reaction=Subquery(my, output_field=CharField()))
    return qs


class PostListCreateView(generics.ListCreateAPIView):
    """GET /api/posts/ — paginated list. POST /api/posts/ — create (auth)."""
    permission_classes = [IsAuthenticatedOrReadOnly]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return PostCreateUpdateSerializer
        return PostListSerializer

    def get_queryset(self):
        viewer = self.request.user if self.request.user.is_authenticated else None
        qs = _post_queryset_with_counts(viewer=viewer).order_by('-created_at')
        params = self.request.query_params

        author = params.get('author')
        if author:
            qs = qs.filter(author_id=author)

        specialization = params.get('specialization')
        if specialization:
            qs = qs.filter(specializations__id=specialization).distinct()

        q = params.get('q')
        if q:
            qs = qs.filter(content__icontains=q)

        return qs

    @extend_schema(
        tags=['Posts'],
        operation_id='posts_01_list',
        summary="List posts",
        description="Paginated newest-first list of posts. Filters: ?author=, ?specialization=, ?q=. Each post carries likes/dislikes counts and (if authenticated) the viewer's `my_reaction`.",
        responses={200: PostListSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=['Posts'],
        operation_id='posts_02_create',
        summary="Create a post",
        description="Authenticated users only. Requires content (1–5000 chars) and 1–3 specialization UUIDs. Optional file `attachments` via multipart/form-data.",
        request=PostCreateUpdateSerializer,
        responses={
            201: PostDetailSerializer,
            400: OpenApiResponse(description="Validation error."),
            401: OpenApiResponse(description="Authentication required."),
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        post = serializer.save(author=request.user)
        post = _post_queryset_with_counts(viewer=request.user).get(pk=post.pk)
        return Response(
            PostDetailSerializer(post, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


class PostDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET / PATCH / DELETE /api/posts/{id}/."""
    permission_classes = [IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        viewer = self.request.user if self.request.user.is_authenticated else None
        return _post_queryset_with_counts(viewer=viewer)

    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return PostCreateUpdateSerializer
        return PostDetailSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        instance = self.get_queryset().get(pk=instance.pk)
        return Response(PostDetailSerializer(instance, context={'request': request}).data)

    @extend_schema(tags=['Posts'], operation_id='posts_03_detail', summary="Get a post.")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=['Posts'],
        operation_id='posts_04_update',
        summary="Update a post (author only).",
        request=PostCreateUpdateSerializer,
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(
        tags=['Posts'],
        operation_id='posts_05_delete',
        summary="Delete a post (author only). Cascades to attachments and reactions.",
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


class _PostReactionToggleView(APIView):
    """Shared base — concrete subclasses set `target_reaction`."""
    permission_classes = [IsAuthenticated]
    target_reaction = None  # 'like' or 'dislike'

    def _toggle(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        with transaction.atomic():
            existing = (
                PostReaction.objects
                .select_for_update()
                .filter(user=request.user, post=post)
                .first()
            )
            if existing is None:
                PostReaction.objects.create(
                    user=request.user, post=post, reaction=self.target_reaction,
                )
            elif existing.reaction == self.target_reaction:
                existing.delete()
            else:
                existing.reaction = self.target_reaction
                existing.save(update_fields=['reaction', 'updated_at'])

        post = _post_queryset_with_counts(viewer=request.user).get(pk=pk)
        return Response(
            PostDetailSerializer(post, context={'request': request}).data,
            status=status.HTTP_200_OK,
        )


class PostLikeView(_PostReactionToggleView):
    """POST /api/posts/{id}/like/ — toggle like."""
    target_reaction = 'like'

    @extend_schema(
        tags=['Posts'],
        operation_id='posts_06_post_like',
        summary="Toggle like on a post.",
        description=(
            "If the user has no reaction → adds a like. If already liked → removes "
            "the like (toggle off). If currently disliked → switches to like. "
            "Returns the full post detail with updated counts and the viewer's new `my_reaction`."
        ),
        request=None,
        responses={
            200: PostDetailSerializer,
            401: OpenApiResponse(description="Authentication required."),
            404: OpenApiResponse(description="Post not found."),
        },
    )
    def post(self, request, pk):
        return self._toggle(request, pk)


class PostDislikeView(_PostReactionToggleView):
    """POST /api/posts/{id}/dislike/ — toggle dislike."""
    target_reaction = 'dislike'

    @extend_schema(
        tags=['Posts'],
        operation_id='posts_07_post_dislike',
        summary="Toggle dislike on a post.",
        description="Symmetric to like: adds a dislike, toggles off, or switches from like to dislike.",
        request=None,
        responses={
            200: PostDetailSerializer,
            401: OpenApiResponse(description="Authentication required."),
            404: OpenApiResponse(description="Post not found."),
        },
    )
    def post(self, request, pk):
        return self._toggle(request, pk)