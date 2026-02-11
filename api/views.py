"""
Views for Authentication and User Management
"""

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
)
from .models import User


class RegisterView(APIView):
    """
    POST: Register new user (Step 1: Send OTP)
    
    Validates registration data and sends OTP to email.
    User account is NOT created yet.
    """
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
    """
    POST: Verify OTP and create user account (Step 2: Complete Registration)
    
    If OTP is valid:
    - Creates user account
    - Auto-login (returns JWT tokens)
    - Returns user profile with wallet and specializations
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        
        if serializer.is_valid():
            # User was created in serializer validation
            user = serializer.validated_data['user']
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            
            # Get user details
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
    """
    POST: User login
    
    Login with email or username.
    Includes rate limiting (5 attempts, 15 min lockout).
    Blocks unverified emails.
    Returns JWT tokens and user profile with wallet balance.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            
            # Get user details with wallet and specializations
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
    """
    POST: Resend OTP to email
    
    Rate limited: 60 seconds between requests
    Maximum 3 resend attempts
    """
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
    """
    GET: Get current user's profile
    PATCH: Update current user's profile
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get current user's profile"""
        serializer = UserDetailSerializer(request.user, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def patch(self, request):
        """Update current user's profile"""
        # TODO: Implement profile update logic
        return Response(
            {"message": "Profile update not yet implemented"},
            status=status.HTTP_501_NOT_IMPLEMENTED
        )