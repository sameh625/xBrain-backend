from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.exceptions import ValidationError as DRFValidationError, PermissionDenied
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.contrib.auth import authenticate
from django.core.cache import cache
from django.db import transaction
from django.db.models import Count, Q, OuterRef, Subquery, CharField
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .authentication import access_blacklist_key

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
    CommentSerializer,
    CommentCreateSerializer,
    CommentUpdateSerializer,
    CertificateSerializer,
    PublicUserProfileSerializer,
    SpecializationCompactSerializer,
    MeetingRequestSerializer,
    MeetingRequestCreateSerializer,
    MeetingRequestAcceptSerializer,
    MeetingRequestDeclineSerializer,
    SeenPostsInSerializer,
    SeenQuestionsInSerializer,
)
from .models import (
    User, Specialization, UserSpecialization,
    Question, Answer, Post, PostReaction, Comment, Certificate,
    MeetingRequest, SeenPost, SeenQuestion, PointsWallet,
)
from .permissions import IsAuthorOrReadOnly, IsQuestionAuthor, IsCommentDeletable


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

        # Also blacklist the *access* token used for this request so it
        # can't be reused until it would have naturally expired.
        access = request.auth
        if access is not None:
            jti = access.get('jti')
            exp = access.get('exp')
            if jti and exp:
                ttl = int(exp - timezone.now().timestamp())
                if ttl > 0:
                    cache.set(access_blacklist_key(jti), '1', timeout=ttl)

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
        viewer = self.request.user if self.request.user.is_authenticated else None
        qs = _question_queryset_with_counts()
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

        if viewer is not None:
            from .utils import annotate_ranking
            # Engagement for questions = answers_count (proxy for both reactions
            # and comments since questions have neither).
            qs = annotate_ranking(
                qs, viewer,
                engagement_field='answers_count',
                seen_model=SeenQuestion,
                seen_target_field='question',
            )
        else:
            qs = qs.order_by('-created_at')
        return qs

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @extend_schema(
        tags=['Q&A'],
        operation_id='qa_01_questions_list',
        summary="List questions (ranked feed for authenticated viewers)",
        description=(
            "Paginated list of questions. For authenticated viewers the list "
            "is ordered by a personalized score (specialization match + "
            "recency − already-seen + answer engagement). Anonymous viewers "
            "get pure newest-first. Filters: ?author=, ?specialization=, "
            "?is_resolved=, ?q=."
        ),
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
        if instance.is_blocked:
            raise DRFValidationError(
                "This question is locked by an active meeting request and cannot be edited. "
                "Cancel the meeting request first."
            )
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        instance = self.get_queryset().get(pk=instance.pk)
        return Response(QuestionDetailSerializer(instance, context={'request': request}).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_blocked:
            raise DRFValidationError(
                "This question is locked by an active meeting request and cannot be deleted. "
                "Cancel the meeting request first."
            )
        return super().destroy(request, *args, **kwargs)

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
        summary="Update a question (author only). Forbidden while the question is blocked by an active meeting request.",
        request=QuestionCreateUpdateSerializer,
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(
        tags=['Q&A'],
        operation_id='qa_05_question_delete',
        summary="Delete a question (author only). Forbidden while the question is blocked by an active meeting request. Cascades to answers and replies.",
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


class QuestionResolveView(APIView):
    """POST /api/questions/{id}/resolve/ — asker only.

    Triggers the point transfer from asker → answerer (the meet attendee).
    Requires the question to be currently blocked by a SCHEDULED meeting whose
    `scheduled_at` time has already arrived. Not idempotent in the points
    sense: a second call on an already-transferred question is a no-op."""
    permission_classes = [IsAuthenticated, IsQuestionAuthor]

    @extend_schema(
        tags=['Q&A'],
        operation_id='qa_06_question_resolve',
        summary="Mark a question as resolved and transfer points (asker only).",
        description=(
            "Resolving a question transfers the booked points from the asker's "
            "wallet to the answerer (the user who attended the scheduled meet). "
            "Requires that the question is blocked by a SCHEDULED meeting and "
            "that the meeting's `scheduled_at` time has already passed."
        ),
        responses={
            200: QuestionDetailSerializer,
            400: OpenApiResponse(description="Question is not blocked by a scheduled meet, or the meet time has not yet arrived."),
            403: OpenApiResponse(description="Only the question's author may resolve it."),
            404: OpenApiResponse(description="Question not found."),
        },
        request=None,
    )
    def post(self, request, pk):
        question = get_object_or_404(Question, pk=pk)
        self.check_object_permissions(request, question)

        if question.is_transferred:
            # Already done — return current state idempotently.
            question = _question_queryset_with_counts().get(pk=pk)
            return Response(
                QuestionDetailSerializer(question, context={'request': request}).data,
                status=status.HTTP_200_OK,
            )

        if not question.is_blocked or question.answerer_id is None:
            raise DRFValidationError(
                "Cannot resolve — no scheduled meeting on this question. "
                "Request a meeting and wait for the answerer to accept first."
            )

        scheduled_meet = (
            MeetingRequest.objects
            .filter(answer__question=question, status=MeetingRequest.STATUS_SCHEDULED)
            .order_by('-created_at')
            .first()
        )
        if scheduled_meet is None or scheduled_meet.scheduled_at is None:
            raise DRFValidationError(
                "Cannot resolve — no scheduled meeting found on this question."
            )
        if timezone.now() < scheduled_meet.scheduled_at:
            raise DRFValidationError(
                "Cannot resolve — the meeting time has not arrived yet."
            )

        with transaction.atomic():
            # Lock the wallets to avoid double-spend if concurrent requests collide.
            asker_wallet = PointsWallet.objects.select_for_update().get(user=request.user)
            answerer_wallet = PointsWallet.objects.select_for_update().get(
                user=scheduled_meet.answerer,
            )
            amount = question.booked_amount
            if amount > 0:
                if asker_wallet.balance < amount:
                    # Defensive — booking should already guarantee this, but a
                    # manual admin adjustment could break the invariant.
                    raise DRFValidationError(
                        "Cannot resolve — asker wallet balance is below the booked amount."
                    )
                asker_wallet.balance -= amount
                asker_wallet.save(update_fields=['balance'])
                answerer_wallet.balance += amount
                answerer_wallet.save(update_fields=['balance'])

            question.is_resolved = True
            question.is_transferred = True
            question.resolved_at = timezone.now()
            question.save(update_fields=[
                'is_resolved', 'is_transferred', 'resolved_at', 'updated_at',
            ])

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

        if question.is_transferred:
            raise DRFValidationError(
                "Cannot unresolve — points have already been transferred for this question."
            )

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
        .prefetch_related('specializations', 'attachments', 'comments')
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
            comments_count=Count('comments', distinct=True),
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
        qs = _post_queryset_with_counts(viewer=viewer)
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

        # Personalized ranking for authenticated viewers; anonymous viewers
        # still get pure recency (cheap and avoids needing user specializations).
        if viewer is not None:
            from django.db.models import F, FloatField, ExpressionWrapper
            from .utils import annotate_ranking
            # Engagement for posts = likes + dislikes + comments.
            qs = qs.annotate(
                engagement=ExpressionWrapper(
                    F('likes_count') + F('dislikes_count') + F('comments_count'),
                    output_field=FloatField(),
                ),
            )
            qs = annotate_ranking(
                qs, viewer,
                engagement_field='engagement',
                seen_model=SeenPost,
                seen_target_field='post',
            )
        else:
            qs = qs.order_by('-created_at')
        return qs

    @extend_schema(
        tags=['Posts'],
        operation_id='posts_01_list',
        summary="List posts (ranked feed for authenticated viewers)",
        description=(
            "Paginated list of posts. For authenticated viewers the list is "
            "ordered by a personalized score (specialization match + recency − "
            "already-seen + engagement). Anonymous viewers get pure newest-first. "
            "Filters: ?author=, ?specialization=, ?q=. Each post carries "
            "likes/dislikes counts and (if authenticated) the viewer's `my_reaction`."
        ),
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


class MarkPostsSeenView(APIView):
    """POST /api/posts/seen/ — bulk-mark posts as seen by the current user.

    The Flutter client calls this with the IDs of posts that actually rendered
    on screen; the ranked feed then demotes them on subsequent pages."""
    permission_classes = [IsAuthenticated]
    serializer_class = SeenPostsInSerializer

    @extend_schema(
        tags=['Posts'],
        operation_id='posts_08_mark_seen',
        summary="Mark posts as seen by the current user (ranked feed signal).",
        description=(
            "Body: `{\"post_ids\": [\"uuid\", ...]}`. Unknown IDs are silently "
            "ignored. Idempotent — calling twice with the same IDs just refreshes "
            "their `seen_at`. The ranked feed uses this to demote already-seen "
            "posts on future requests."
        ),
        request=SeenPostsInSerializer,
        responses={
            204: OpenApiResponse(description="Seen state recorded."),
            400: OpenApiResponse(description="Malformed input or too many IDs."),
            401: OpenApiResponse(description="Authentication required."),
        },
    )
    def post(self, request):
        serializer = SeenPostsInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        post_ids = serializer.validated_data['post_ids']

        # Filter to existing posts so we don't create FKs to nothing.
        known_ids = list(Post.objects.filter(id__in=post_ids).values_list('id', flat=True))
        if known_ids:
            SeenPost.objects.bulk_create(
                [SeenPost(user=request.user, post_id=pid) for pid in known_ids],
                update_conflicts=True,
                unique_fields=['user', 'post'],
                update_fields=['seen_at'],
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class MarkQuestionsSeenView(APIView):
    """POST /api/questions/seen/ — bulk-mark questions as seen by the current user."""
    permission_classes = [IsAuthenticated]
    serializer_class = SeenQuestionsInSerializer

    @extend_schema(
        tags=['Q&A'],
        operation_id='qa_16_mark_seen',
        summary="Mark questions as seen by the current user (ranked feed signal).",
        description=(
            "Body: `{\"question_ids\": [\"uuid\", ...]}`. Unknown IDs are silently "
            "ignored. Idempotent — calling twice with the same IDs just refreshes "
            "their `seen_at`. The ranked feed uses this to demote already-seen "
            "questions on future requests."
        ),
        request=SeenQuestionsInSerializer,
        responses={
            204: OpenApiResponse(description="Seen state recorded."),
            400: OpenApiResponse(description="Malformed input or too many IDs."),
            401: OpenApiResponse(description="Authentication required."),
        },
    )
    def post(self, request):
        serializer = SeenQuestionsInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        question_ids = serializer.validated_data['question_ids']

        known_ids = list(Question.objects.filter(id__in=question_ids).values_list('id', flat=True))
        if known_ids:
            SeenQuestion.objects.bulk_create(
                [SeenQuestion(user=request.user, question_id=qid) for qid in known_ids],
                update_conflicts=True,
                unique_fields=['user', 'question'],
                update_fields=['seen_at'],
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


# =====================================================================
# Certificates (Sprint 2 — Item 4)
#
# The model already shipped in Sprint 1; only endpoints are new.
# =====================================================================


class MyCertificatesListCreateView(generics.ListCreateAPIView):
    """GET /api/users/me/certificates/  — my certificates.
    POST /api/users/me/certificates/ — add a new certificate (URL or file)."""
    permission_classes = [IsAuthenticated]
    serializer_class = CertificateSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        return Certificate.objects.filter(user=self.request.user).order_by('-issue_date')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @extend_schema(
        tags=['Users'],
        operation_id='users_06_my_certificates_list',
        summary="List my certificates",
        description="Returns the authenticated user's certificates, newest issue date first.",
        responses={200: CertificateSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=['Users'],
        operation_id='users_07_my_certificate_create',
        summary="Add a certificate",
        description=(
            "Authenticated users only. Provide at least one of `certificate_url` "
            "(external link) or `certificate_file` (PDF or image upload). Both are allowed. "
            "Use application/json for URL-only certificates; use multipart/form-data when "
            "uploading a file. The owning user is taken from the request — never from the body."
        ),
        request={
            'application/json': CertificateSerializer,
            'multipart/form-data': CertificateSerializer,
        },
        responses={
            201: CertificateSerializer,
            400: OpenApiResponse(description="Validation error (e.g., missing both URL and file, file too large, unsupported file type)."),
            401: OpenApiResponse(description="Authentication required."),
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class MyCertificateDeleteView(generics.DestroyAPIView):
    """DELETE /api/users/me/certificates/{id}/ — delete one of my certificates.

    The queryset is filtered to the current user, so trying to delete someone
    else's certificate by guessing the UUID returns 404, not 403."""
    permission_classes = [IsAuthenticated]
    serializer_class = CertificateSerializer

    def get_queryset(self):
        return Certificate.objects.filter(user=self.request.user)

    @extend_schema(
        tags=['Users'],
        operation_id='users_08_my_certificate_delete',
        summary="Delete one of my certificates",
        responses={
            204: OpenApiResponse(description='Certificate deleted.'),
            401: OpenApiResponse(description="Authentication required."),
            404: OpenApiResponse(description="Not found (or not yours)."),
        },
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


class UserCertificatesPublicView(generics.ListAPIView):
    """GET /api/users/{user_id}/certificates/ — public list of any user's certificates.

    Read-only and anyone (anonymous OK) can view. Useful for showing a profile
    page's credentials. Authenticated callers see the same data as anonymous."""
    permission_classes = [IsAuthenticatedOrReadOnly]
    serializer_class = CertificateSerializer

    def get_queryset(self):
        return Certificate.objects.filter(
            user_id=self.kwargs['user_id']
        ).order_by('-issue_date')

    @extend_schema(
        tags=['Users'],
        operation_id='users_09_user_certificates',
        summary="List a user's certificates (public)",
        description="Returns certificates for the user identified by the URL UUID. Public — no auth required.",
        responses={200: CertificateSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# User-scoped feeds (my posts/questions, other-user posts/questions, profile)
# ─────────────────────────────────────────────────────────────────────────────

class MyPostsListView(generics.ListAPIView):
    """GET /api/users/me/posts/ — current user's authored posts, newest first."""
    permission_classes = [IsAuthenticated]
    serializer_class = PostListSerializer

    def get_queryset(self):
        return (
            _post_queryset_with_counts(viewer=self.request.user)
            .filter(author=self.request.user)
            .order_by('-created_at')
        )

    @extend_schema(
        tags=['Users'],
        operation_id='users_10_my_posts',
        summary="List the current user's posts",
        description="Paginated, newest-first list of posts authored by the authenticated user.",
        responses={200: PostListSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class MyQuestionsListView(generics.ListAPIView):
    """GET /api/users/me/questions/ — current user's authored questions, newest first."""
    permission_classes = [IsAuthenticated]
    serializer_class = QuestionListSerializer

    def get_queryset(self):
        return (
            _question_queryset_with_counts()
            .filter(author=self.request.user)
            .order_by('-created_at')
        )

    @extend_schema(
        tags=['Users'],
        operation_id='users_11_my_questions',
        summary="List the current user's questions",
        description="Paginated, newest-first list of questions authored by the authenticated user.",
        responses={200: QuestionListSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class UserPostsListView(generics.ListAPIView):
    """GET /api/users/{user_id}/posts/ — any user's authored posts, newest first."""
    permission_classes = [IsAuthenticated]
    serializer_class = PostListSerializer

    def get_queryset(self):
        # 404 if the user doesn't exist
        get_object_or_404(User, pk=self.kwargs['user_id'])
        return (
            _post_queryset_with_counts(viewer=self.request.user)
            .filter(author_id=self.kwargs['user_id'])
            .order_by('-created_at')
        )

    @extend_schema(
        tags=['Users'],
        operation_id='users_12_user_posts',
        summary="List a user's posts",
        description="Paginated, newest-first list of posts authored by the user identified by the URL UUID.",
        responses={
            200: PostListSerializer(many=True),
            404: OpenApiResponse(description="User not found."),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class UserQuestionsListView(generics.ListAPIView):
    """GET /api/users/{user_id}/questions/ — any user's authored questions, newest first."""
    permission_classes = [IsAuthenticated]
    serializer_class = QuestionListSerializer

    def get_queryset(self):
        get_object_or_404(User, pk=self.kwargs['user_id'])
        return (
            _question_queryset_with_counts()
            .filter(author_id=self.kwargs['user_id'])
            .order_by('-created_at')
        )

    @extend_schema(
        tags=['Users'],
        operation_id='users_13_user_questions',
        summary="List a user's questions",
        description="Paginated, newest-first list of questions authored by the user identified by the URL UUID.",
        responses={
            200: QuestionListSerializer(many=True),
            404: OpenApiResponse(description="User not found."),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class UserProfileDetailView(generics.RetrieveAPIView):
    """GET /api/users/{user_id}/ — public profile of any user."""
    permission_classes = [IsAuthenticated]
    serializer_class = PublicUserProfileSerializer
    queryset = User.objects.all()
    lookup_url_kwarg = 'user_id'

    @extend_schema(
        tags=['Users'],
        operation_id='users_14_user_profile_public',
        summary="Get a user's public profile",
        description=(
            "Returns the public profile (no email, phone, or wallet) of the user identified "
            "by the URL UUID. Includes the user's specializations (by name) and counts of "
            "their authored posts and questions."
        ),
        responses={
            200: PublicUserProfileSerializer,
            404: OpenApiResponse(description="User not found."),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class UserPublicSpecializationsView(generics.ListAPIView):
    """GET /api/users/{user_id}/specializations/ — public list of a user's specializations."""
    permission_classes = [IsAuthenticated]
    serializer_class = SpecializationCompactSerializer
    pagination_class = None  # specializations are few — return them all

    def get_queryset(self):
        get_object_or_404(User, pk=self.kwargs['user_id'])
        return Specialization.objects.filter(
            specialization_users__user_id=self.kwargs['user_id']
        ).order_by('name')

    @extend_schema(
        tags=['Users'],
        operation_id='users_15_user_specializations',
        summary="List a user's specializations (public)",
        description="Returns the specializations of the user identified by the URL UUID.",
        responses={
            200: SpecializationCompactSerializer(many=True),
            404: OpenApiResponse(description="User not found."),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


def _comment_queryset_with_counts():
    return (
        Comment.objects
        .select_related('author', 'post')
        .annotate(replies_count=Count('replies'))
    )


class CommentListCreateView(generics.ListCreateAPIView):
    """GET / POST /api/posts/{post_id}/comments/ — top-level comments only."""
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CommentCreateSerializer
        return CommentSerializer

    def get_queryset(self):
        post_id = self.kwargs['post_id']
        get_object_or_404(Post, pk=post_id)
        return (
            _comment_queryset_with_counts()
            .filter(post_id=post_id, parent_comment__isnull=True)
            .order_by('created_at')
        )

    def create(self, request, *args, **kwargs):
        post = get_object_or_404(Post, pk=self.kwargs['post_id'])
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = serializer.save(
            author=request.user,
            post=post,
            parent_comment=None,
        )
        comment = _comment_queryset_with_counts().get(pk=comment.pk)
        return Response(
            CommentSerializer(comment, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        tags=['Posts'],
        operation_id='posts_08_comments_list',
        summary="List top-level comments under a post.",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=['Posts'],
        operation_id='posts_09_comment_create',
        summary="Post a top-level comment on a post.",
        request=CommentCreateSerializer,
        responses={
            201: CommentSerializer,
            400: OpenApiResponse(description="Validation error."),
            401: OpenApiResponse(description="Authentication required."),
            404: OpenApiResponse(description="Post not found."),
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class CommentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET / PATCH / DELETE /api/comments/{id}/ — works for both top-level
    comments and replies. Delete permission: comment author OR post author."""
    permission_classes = [IsAuthenticatedOrReadOnly, IsCommentDeletable]
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        return _comment_queryset_with_counts()

    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return CommentUpdateSerializer
        return CommentSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        instance = self.get_queryset().get(pk=instance.pk)
        return Response(CommentSerializer(instance, context={'request': request}).data)

    @extend_schema(tags=['Posts'], operation_id='posts_10_comment_detail', summary="Get a comment or reply.")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=['Posts'],
        operation_id='posts_11_comment_update',
        summary="Edit a comment or reply (author only). Content only.",
        request=CommentUpdateSerializer,
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(
        tags=['Posts'],
        operation_id='posts_12_comment_delete',
        summary="Delete a comment/reply (author OR post-author). Cascades to replies.",
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


class CommentReplyListCreateView(generics.ListCreateAPIView):
    """GET / POST /api/comments/{id}/replies/ — replies under a top-level comment."""
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CommentCreateSerializer
        return CommentSerializer

    def get_queryset(self):
        parent_id = self.kwargs['pk']
        get_object_or_404(Comment, pk=parent_id)
        return (
            _comment_queryset_with_counts()
            .filter(parent_comment_id=parent_id)
            .order_by('created_at')
        )

    def create(self, request, *args, **kwargs):
        parent = get_object_or_404(Comment, pk=self.kwargs['pk'])

        # Depth-1 enforcement.
        if parent.parent_comment_id is not None:
            raise DRFValidationError(
                {"parent_comment": "Replies cannot have replies — depth limit is 1."}
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reply = serializer.save(
            author=request.user,
            post=parent.post,
            parent_comment=parent,
        )
        reply = _comment_queryset_with_counts().get(pk=reply.pk)
        return Response(
            CommentSerializer(reply, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(tags=['Posts'], operation_id='posts_13_replies_list', summary="List replies under a comment.")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=['Posts'],
        operation_id='posts_14_reply_create',
        summary="Post a reply to a comment.",
        description="The parent must be a top-level comment (depth-1 limit). Replying to a reply returns 400.",
        request=CommentCreateSerializer,
        responses={
            201: CommentSerializer,
            400: OpenApiResponse(description="Cannot reply to a reply (depth-1 limit)."),
            401: OpenApiResponse(description="Authentication required."),
            404: OpenApiResponse(description="Parent comment not found."),
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# Meeting Requests — Google Meet for Q&A live explanations
# ─────────────────────────────────────────────────────────────────────────────

def _meeting_queryset():
    """Optimized queryset for meeting list/detail views (avoids N+1)."""
    return (
        MeetingRequest.objects
        .select_related('asker', 'answerer', 'answer__question')
    )


class RequestMeetingView(APIView):
    """POST /api/answers/{id}/request-meeting/ — asker asks for a live meeting.

    Only the original question's author (the asker) can request a meeting on
    an answer to their question.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = MeetingRequestCreateSerializer

    @extend_schema(
        tags=['Meetings'],
        operation_id='meetings_04_request',
        summary="Request a live meeting on an answer (books points from asker's wallet)",
        description=(
            "The question's author proposes 1–5 time slots to the answerer. "
            "Only the question's author may call this. **Books the question's "
            "cost from the asker's available wallet balance** and locks the "
            "question (no further meets, no edits, no deletes) until the "
            "request is declined, cancelled, or the question is resolved."
        ),
        request=MeetingRequestCreateSerializer,
        responses={
            201: MeetingRequestSerializer,
            400: OpenApiResponse(description="Validation error, duplicate active request, or question already blocked."),
            402: OpenApiResponse(description="Insufficient available points balance to book this meeting."),
            403: OpenApiResponse(description="Only the question's author may request a meeting."),
            404: OpenApiResponse(description="Answer not found."),
        },
    )
    def post(self, request, pk):
        answer = get_object_or_404(
            Answer.objects.select_related('question__author', 'author'),
            pk=pk,
        )

        # Permission: only the question's author can request meetings on its answers.
        if answer.question.author_id != request.user.id:
            raise PermissionDenied(
                "Only the question's author may request a meeting on its answers."
            )

        # Sanity: can't request a meeting from yourself.
        if answer.author_id == request.user.id:
            raise DRFValidationError("You cannot request a meeting on your own answer.")

        # Refuse if an active (pending or scheduled) request already exists.
        existing = MeetingRequest.objects.filter(
            answer=answer,
            asker=request.user,
            status__in=[MeetingRequest.STATUS_PENDING, MeetingRequest.STATUS_SCHEDULED],
        ).first()
        if existing:
            raise DRFValidationError(
                "An active meeting request already exists for this answer. "
                "Cancel it before creating a new one."
            )

        serializer = MeetingRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from .utils import compute_question_cost, send_meeting_request_created_email

        with transaction.atomic():
            # Lock the question row so two concurrent requests on different
            # answers of the same question can't both book the same wallet slot.
            question = Question.objects.select_for_update().get(pk=answer.question_id)
            if question.is_blocked:
                raise DRFValidationError(
                    "This question is already locked by another active meeting request."
                )

            cost = compute_question_cost(question.specializations.all())
            if request.user.available_balance < cost:
                return Response(
                    {
                        'error': (
                            f'Insufficient points. Need {cost} points to book this meeting; '
                            f'you have {request.user.available_balance} available '
                            f'(wallet balance minus points already booked on other meetings).'
                        ),
                        'required': cost,
                        'available': request.user.available_balance,
                    },
                    status=status.HTTP_402_PAYMENT_REQUIRED,
                )

            meeting_request = MeetingRequest.objects.create(
                answer=answer,
                asker=request.user,
                answerer=answer.author,
                duration_minutes=serializer.validated_data['duration_minutes'],
                proposed_slots=serializer.validated_data['proposed_slots'],
                message=serializer.validated_data.get('message', ''),
                status=MeetingRequest.STATUS_PENDING,
            )

            question.is_blocked = True
            question.booked_amount = cost
            question.answerer = answer.author
            question.save(update_fields=[
                'is_blocked', 'booked_amount', 'answerer', 'updated_at',
            ])

        # Notify the answerer (failure is logged but doesn't block creation).
        send_meeting_request_created_email(meeting_request)

        return Response(
            MeetingRequestSerializer(meeting_request).data,
            status=status.HTTP_201_CREATED,
        )


class AcceptMeetingView(APIView):
    """POST /api/meeting-requests/{id}/accept/ — answerer picks one of the slots.

    Backend creates a Google Calendar event with an auto-generated Meet link
    and notifies both parties via email.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = MeetingRequestAcceptSerializer

    @extend_schema(
        tags=['Meetings'],
        operation_id='meetings_05_accept',
        summary="Accept one of the proposed slots",
        description=(
            "Only the answerer can call this. The chosen slot must be one of "
            "the originally proposed datetimes. On success, the backend creates "
            "a Google Calendar event with an auto-generated Meet link and emails "
            "both parties."
        ),
        request=MeetingRequestAcceptSerializer,
        responses={
            200: MeetingRequestSerializer,
            400: OpenApiResponse(description="Slot not in proposed list, or request not in pending state."),
            403: OpenApiResponse(description="Only the answerer may accept."),
            404: OpenApiResponse(description="Meeting request not found."),
            502: OpenApiResponse(description="Failed to create the Google Meet link."),
        },
    )
    def post(self, request, pk):
        meeting_request = get_object_or_404(_meeting_queryset(), pk=pk)

        if meeting_request.answerer_id != request.user.id:
            raise PermissionDenied("Only the answerer may accept this meeting request.")
        if meeting_request.status != MeetingRequest.STATUS_PENDING:
            raise DRFValidationError(
                f"Cannot accept — meeting request is already {meeting_request.status}."
            )

        serializer = MeetingRequestAcceptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        chosen_slot = serializer.validated_data['scheduled_at']

        # Chosen slot must be one of the originally proposed ones (exact match).
        proposed_iso = {s.isoformat() for s in meeting_request.proposed_slots}
        if chosen_slot.isoformat() not in proposed_iso:
            raise DRFValidationError({
                'scheduled_at': ['Chosen slot must be one of the originally proposed slots.']
            })

        # Create the Google Calendar event + Meet link.
        from .google_meet import create_meet_event, GoogleMeetError
        from .utils import send_meeting_scheduled_email

        asker_name = f"{meeting_request.asker.first_name} {meeting_request.asker.last_name}".strip() \
                     or meeting_request.asker.username
        answerer_name = f"{meeting_request.answerer.first_name} {meeting_request.answerer.last_name}".strip() \
                        or meeting_request.answerer.username
        summary = f"xBrain — {asker_name} & {answerer_name}"
        description = (
            f"Live discussion of the following xBrain question:\n\n"
            f"\"{meeting_request.answer.question.content[:500]}\"\n\n"
            f"{'Asker message: ' + meeting_request.message if meeting_request.message else ''}"
        )

        try:
            meet_link, event_id = create_meet_event(
                summary=summary,
                description=description,
                starts_at=chosen_slot,
                duration_minutes=meeting_request.duration_minutes,
                attendee_emails=[
                    meeting_request.asker.email,
                    meeting_request.answerer.email,
                ],
            )
        except GoogleMeetError as e:
            return Response(
                {'error': f'Failed to create Google Meet event: {e}'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        with transaction.atomic():
            meeting_request.scheduled_at = chosen_slot
            meeting_request.meet_link = meet_link
            meeting_request.google_event_id = event_id
            meeting_request.status = MeetingRequest.STATUS_SCHEDULED
            meeting_request.save(update_fields=[
                'scheduled_at', 'meet_link', 'google_event_id', 'status', 'updated_at',
            ])

        send_meeting_scheduled_email(meeting_request)

        return Response(
            MeetingRequestSerializer(meeting_request).data,
            status=status.HTTP_200_OK,
        )


class DeclineMeetingView(APIView):
    """POST /api/meeting-requests/{id}/decline/ — answerer declines all slots."""
    permission_classes = [IsAuthenticated]
    serializer_class = MeetingRequestDeclineSerializer

    @extend_schema(
        tags=['Meetings'],
        operation_id='meetings_06_decline',
        summary="Decline a meeting request",
        description="Only the answerer can call this. Optional short message to the asker.",
        request=MeetingRequestDeclineSerializer,
        responses={
            200: MeetingRequestSerializer,
            400: OpenApiResponse(description="Request is not in pending state."),
            403: OpenApiResponse(description="Only the answerer may decline."),
            404: OpenApiResponse(description="Meeting request not found."),
        },
    )
    def post(self, request, pk):
        meeting_request = get_object_or_404(_meeting_queryset(), pk=pk)

        if meeting_request.answerer_id != request.user.id:
            raise PermissionDenied("Only the answerer may decline this meeting request.")
        if meeting_request.status != MeetingRequest.STATUS_PENDING:
            raise DRFValidationError(
                f"Cannot decline — meeting request is already {meeting_request.status}."
            )

        serializer = MeetingRequestDeclineSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            meeting_request.status = MeetingRequest.STATUS_DECLINED
            meeting_request.decline_message = serializer.validated_data.get('message', '')
            meeting_request.save(update_fields=['status', 'decline_message', 'updated_at'])

            # Release the booking on the question so the asker can try again
            # with a different answer's author.
            question = Question.objects.select_for_update().get(
                pk=meeting_request.answer.question_id
            )
            if question.is_blocked and not question.is_transferred:
                question.is_blocked = False
                question.booked_amount = 0
                question.answerer = None
                question.save(update_fields=[
                    'is_blocked', 'booked_amount', 'answerer', 'updated_at',
                ])

        from .utils import send_meeting_declined_email
        send_meeting_declined_email(meeting_request)

        return Response(
            MeetingRequestSerializer(meeting_request).data,
            status=status.HTTP_200_OK,
        )


class CancelMeetingView(APIView):
    """POST /api/meeting-requests/{id}/cancel/ — asker cancels their own request.

    If the meeting was already scheduled, the associated Google Calendar
    event is also cancelled.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Meetings'],
        operation_id='meetings_07_cancel',
        summary="Cancel a meeting request",
        description=(
            "Only the asker can cancel. If the meeting was already scheduled, "
            "the associated Google Calendar event is also cancelled and both "
            "parties get an email."
        ),
        request=None,
        responses={
            200: MeetingRequestSerializer,
            400: OpenApiResponse(description="Request is already declined or cancelled."),
            403: OpenApiResponse(description="Only the asker may cancel."),
            404: OpenApiResponse(description="Meeting request not found."),
        },
    )
    def post(self, request, pk):
        meeting_request = get_object_or_404(_meeting_queryset(), pk=pk)

        if meeting_request.asker_id != request.user.id:
            raise PermissionDenied("Only the asker may cancel this meeting request.")
        if meeting_request.status in (MeetingRequest.STATUS_DECLINED, MeetingRequest.STATUS_CANCELLED):
            raise DRFValidationError(
                f"Cannot cancel — meeting request is already {meeting_request.status}."
            )

        # If already scheduled, also cancel the Google Calendar event.
        if meeting_request.status == MeetingRequest.STATUS_SCHEDULED and meeting_request.google_event_id:
            from .google_meet import cancel_meet_event
            cancel_meet_event(meeting_request.google_event_id)

        with transaction.atomic():
            meeting_request.status = MeetingRequest.STATUS_CANCELLED
            meeting_request.save(update_fields=['status', 'updated_at'])

            # Release the booking — refunds the asker's available balance.
            question = Question.objects.select_for_update().get(
                pk=meeting_request.answer.question_id
            )
            if question.is_blocked and not question.is_transferred:
                question.is_blocked = False
                question.booked_amount = 0
                question.answerer = None
                question.save(update_fields=[
                    'is_blocked', 'booked_amount', 'answerer', 'updated_at',
                ])

        from .utils import send_meeting_cancelled_email
        send_meeting_cancelled_email(meeting_request)

        return Response(
            MeetingRequestSerializer(meeting_request).data,
            status=status.HTTP_200_OK,
        )


class MyOutgoingMeetingRequestsView(generics.ListAPIView):
    """GET /api/users/me/meeting-requests/outgoing/ — requests I sent (I'm the asker)."""
    permission_classes = [IsAuthenticated]
    serializer_class = MeetingRequestSerializer

    def get_queryset(self):
        return (
            _meeting_queryset()
            .filter(asker=self.request.user)
            .order_by('-created_at')
        )

    @extend_schema(
        tags=['Meetings'],
        operation_id='meetings_01_outgoing',
        summary="List meeting requests I sent",
        description="Paginated list of meeting requests where I am the asker. Newest first.",
        responses={200: MeetingRequestSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class MyIncomingMeetingRequestsView(generics.ListAPIView):
    """GET /api/users/me/meeting-requests/incoming/ — requests sent to me (I'm the answerer)."""
    permission_classes = [IsAuthenticated]
    serializer_class = MeetingRequestSerializer

    def get_queryset(self):
        return (
            _meeting_queryset()
            .filter(answerer=self.request.user)
            .order_by('-created_at')
        )

    @extend_schema(
        tags=['Meetings'],
        operation_id='meetings_02_incoming',
        summary="List meeting requests sent to me",
        description="Paginated list of meeting requests where I am the answerer. Newest first.",
        responses={200: MeetingRequestSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class MeetingRequestDetailView(generics.RetrieveAPIView):
    """GET /api/meeting-requests/{id}/ — detail. Only the asker or answerer may view."""
    permission_classes = [IsAuthenticated]
    serializer_class = MeetingRequestSerializer

    def get_queryset(self):
        return _meeting_queryset().filter(
            Q(asker=self.request.user) | Q(answerer=self.request.user)
        )

    @extend_schema(
        tags=['Meetings'],
        operation_id='meetings_03_detail',
        summary="Get a meeting request's detail",
        description="Only the asker or the answerer may view a meeting request.",
        responses={
            200: MeetingRequestSerializer,
            404: OpenApiResponse(description="Meeting request not found, or you are neither the asker nor the answerer."),
        },
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
