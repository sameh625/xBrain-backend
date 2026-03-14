from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter
from django.contrib.auth import authenticate

from .serializers import (
    UserRegistrationSerializer,
    VerifyOTPSerializer,
    UserLoginSerializer,
    ResendOTPSerializer,
    UserDetailSerializer,
    SpecializationSerializer,
    UserSpecializationSerializer,
    ForgotPasswordSerializer,
    VerifyResetOTPSerializer,
    ResetPasswordSerializer,
)
from .models import User, Specialization, UserSpecialization

auth_param = OpenApiParameter(
    name='Authorization',
    description='Bearer token (e.g., Bearer <your_access_token>)',
    required=True,
    type=str,
    location=OpenApiParameter.HEADER
)


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

    @extend_schema(
        summary="Get current user profile",
        description="Returns the profile details of the authenticated user, including their specializations and wallet balance.",
        parameters=[auth_param],
        responses={200: UserDetailSerializer}
    )
    def get(self, request):
        serializer = UserDetailSerializer(request.user, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(exclude=True)
    def patch(self, request):
        return Response(
            {"message": "Profile update not yet implemented"},
            status=status.HTTP_501_NOT_IMPLEMENTED
        )


class SpecializationListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List all specializations",
        description="Returns a list of all available specializations in the system.",
        parameters=[auth_param],
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
        parameters=[auth_param],
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
        parameters=[auth_param],
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
        parameters=[auth_param],
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