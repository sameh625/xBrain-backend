from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.contrib.auth import authenticate
from django.db import transaction
from django.db.models import Count, Q
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
)
from .models import User, Specialization, UserSpecialization, Question, Answer
from .permissions import IsAuthorOrReadOnly, IsQuestionAuthor


class RegisterView(APIView):
    permission_classes = [AllowAny]
    
    @extend_schema(
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
        summary="Get current user profile",
        description="Returns the profile details of the authenticated user, including their specializations and wallet balance.",
        responses={200: UserDetailSerializer}
    )
    def get(self, request):
        serializer = UserDetailSerializer(request.user, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
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

def _question_queryset_with_counts():
    """Annotated queryset used by both list and detail to avoid N+1 on counts.

    `answers_count` is a Facebook-style total: counts top-level answers PLUS replies.
    Same shape as "X comments" on a social media post."""
    return (
        Question.objects
        .select_related('author')
        .prefetch_related('specializations')
        .annotate(
            answers_count=Count('answers', distinct=True),
        )
    )

def _answer_queryset_with_counts():
    return (
        Answer.objects
        .select_related('author', 'question')
        .annotate(replies_count=Count('replies'))
    )


class QuestionListCreateView(generics.ListCreateAPIView):
    """GET /api/questions/ — paginated newest-first list.
    POST /api/questions/ — create a question (auth required)."""
    permission_classes = [IsAuthenticatedOrReadOnly]

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
        summary="List questions",
        description="Paginated newest-first list of questions. Filters: ?author=, ?specialization=, ?is_resolved=, ?q=.",
        responses={200: QuestionListSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=['Q&A'],
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

    @extend_schema(tags=['Q&A'], summary="Get a question with its first 10 answers (and 2 replies each).")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=['Q&A'],
        summary="Update a question (author only)",
        request=QuestionCreateUpdateSerializer,
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(tags=['Q&A'], summary="Delete a question (author only). Cascades to answers and replies.")
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


class QuestionResolveView(APIView):
    """POST /api/questions/{id}/resolve/ — asker only. Idempotent."""
    permission_classes = [IsAuthenticated, IsQuestionAuthor]

    @extend_schema(
        tags=['Q&A'],
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
    POST same URL — create a top-level answer."""
    permission_classes = [IsAuthenticatedOrReadOnly]

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

    @extend_schema(tags=['Q&A'], summary="List top-level answers for a question.")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=['Q&A'],
        summary="Post a top-level answer to a question.",
        request=AnswerCreateSerializer,
        responses={201: AnswerSerializer, 401: OpenApiResponse(description="Authentication required."), 404: OpenApiResponse(description="Question not found.")},
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

class AnswerDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET / PATCH / DELETE /api/answers/{id}/ — works for both top-level answers and replies."""
    permission_classes = [IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]

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

    @extend_schema(tags=['Q&A'], summary="Get a single answer or reply.")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=['Q&A'],
        summary="Update an answer or reply (author only). Only content can be edited.",
        request=AnswerUpdateSerializer,
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(tags=['Q&A'], summary="Delete an answer or reply (author only). Deleting a top-level answer cascades to replies.")
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


class ReplyListCreateView(generics.ListCreateAPIView):
    """GET /api/answers/{id}/replies/ — list replies under a top-level answer.
    POST same URL — post a reply to that answer (depth-1)."""
    permission_classes = [IsAuthenticatedOrReadOnly]

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

    @extend_schema(tags=['Q&A'], summary="List replies under a specific answer.")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=['Q&A'],
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