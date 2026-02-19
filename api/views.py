from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate

from .serializers import (
    UserRegistrationSerializer,
    VerifyOTPSerializer,
    UserLoginSerializer,
    ResendOTPSerializer,
    UserDetailSerializer,
    SpecializationSerializer,
    UserSpecializationSerializer,
)
from .models import User, Specialization, UserSpecialization


class RegisterView(APIView):
    permission_classes = [AllowAny]
    
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

    def get(self, request):
        serializer = UserDetailSerializer(request.user, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        return Response(
            {"message": "Profile update not yet implemented"},
            status=status.HTTP_501_NOT_IMPLEMENTED
        )


class SpecializationListView(APIView):
    permission_classes = [IsAuthenticated]

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

    def put(self, request):
        serializer = UserSpecializationSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        specialization_ids = serializer.validated_data.get('specialization_ids', [])

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