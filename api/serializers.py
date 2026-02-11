"""
Serializers for Authentication and User Management
"""

from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password as django_validate_password
from django.core.exceptions import ValidationError
from .models import User, Specialization, Certificate, PointsWallet
from .utils import validate_password_strength, send_otp_and_store, verify_otp


class UserRegistrationSerializer(serializers.Serializer):
    """
    Serializer for user registration (Step 1: Send OTP)
    Does NOT create user yet - just validates and sends OTP
    """
    email = serializers.EmailField(required=True)
    username = serializers.CharField(required=True, min_length=8, max_length=16)
    password = serializers.CharField(required=True, write_only=True, min_length=8)
    first_name = serializers.CharField(required=True, max_length=50)
    last_name = serializers.CharField(required=True, max_length=50)
    phone_number = serializers.CharField(required=True, max_length=15)
    bio = serializers.CharField(required=False, allow_blank=True, max_length=500)
    profile_image = serializers.ImageField(required=False, allow_null=True)
    
    def validate_email(self, value):
        """Check if email already exists"""
        # Check in pending registrations (cache)
        from django.core.cache import cache
        if cache.get(f'pending_registration_{value}'):
            raise serializers.ValidationError("An OTP has already been sent to this email. Please verify or wait before requesting another.")
        
        # Check in actual users
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already registered.")
        
        return value.lower()
    
    def validate_username(self, value):
        """Check if username already exists and validate format"""
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        
        # Username must start with letter
        if not value[0].isalpha():
            raise serializers.ValidationError("Username must start with a letter.")
        
        # Username can only contain alphanumeric and ._-
        import re
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9._-]*$', value):
            raise serializers.ValidationError("Username can only contain letters, numbers, dots, underscores, and hyphens.")
        
        return value.lower()
    
    def validate_password(self, value):
        """Validate password strength"""
        is_valid, error_message = validate_password_strength(value)
        if not is_valid:
            raise serializers.ValidationError(error_message)
        return value
    
    def validate_phone_number(self, value):
        """Validate phone number format and uniqueness"""
        import re
        if not re.match(r'^\+?[1-9]\d{7,14}$', value):
            raise serializers.ValidationError(
                "Enter a valid phone number (7-15 digits, optional + prefix)."
            )
        
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("This phone number is already registered.")
        
        return value
    
    def create(self, validated_data):
        """
        Store registration data in cache and send OTP
        User is NOT created yet
        """
        email = validated_data['email']
        first_name = validated_data['first_name']
        
        # Store registration data in cache (valid for 10 minutes)
        from django.core.cache import cache
        cache_key = f'pending_registration_{email}'
        cache.set(cache_key, validated_data, timeout=600)  # 10 minutes
        
        # Send OTP
        success, otp, error_message = send_otp_and_store(email, first_name)
        if not success:
            raise serializers.ValidationError({"otp": error_message})
        
        return {
            'email': email,
            'message': 'OTP sent successfully. Please check your email.'
        }


class VerifyOTPSerializer(serializers.Serializer):
    """
    Serializer for OTP verification (Step 2: Verify OTP and create user)
    """
    email = serializers.EmailField(required=True)
    otp = serializers.CharField(required=True, min_length=6, max_length=6)
    
    def validate(self, data):
        """Verify OTP and create user if valid"""
        email = data['email']
        otp = data['otp']
        
        # Verify OTP
        if not verify_otp(email, otp):
            raise serializers.ValidationError({"otp": "Invalid or expired OTP code."})
        
        # Get pending registration data from cache
        from django.core.cache import cache
        cache_key = f'pending_registration_{email}'
        registration_data = cache.get(cache_key)
        
        if not registration_data:
            raise serializers.ValidationError({"email": "Registration data not found. Please register again."})
        
        # Create user
        try:
            user = User.objects.create_user(
                email=registration_data['email'],
                username=registration_data['username'],
                password=registration_data['password'],
                first_name=registration_data['first_name'],
                last_name=registration_data['last_name'],
                phone_number=registration_data['phone_number'],
                bio=registration_data.get('bio', ''),
            )
            
            # Handle profile image if provided
            if 'profile_image' in registration_data and registration_data['profile_image']:
                user.profile_image = registration_data['profile_image']
                user.save()
            
            # Delete pending registration from cache
            cache.delete(cache_key)
            
            # Delete OTP resend counters
            cache.delete(f'otp_resend_count_{email}')
            cache.delete(f'otp_last_sent_{email}')
            
            # Send welcome email
            from .utils import send_welcome_email
            send_welcome_email(
                email=user.email,
                first_name=user.first_name,
                username=user.username
            )
            
            data['user'] = user
            
        except Exception as e:
            raise serializers.ValidationError({"error": f"Failed to create user: {str(e)}"})
        
        return data


class UserLoginSerializer(serializers.Serializer):
    """
    Serializer for user login
    Supports login with email or username
    """
    identifier = serializers.CharField(required=True, help_text="Email or Username")
    password = serializers.CharField(required=True, write_only=True)
    
    def validate(self, data):
        """Validate credentials and authenticate user"""
        identifier = data['identifier'].lower()
        password = data['password']
        
        # Check if account is locked
        from .utils import is_account_locked, increment_login_attempts, reset_login_attempts
        is_locked, attempts, max_attempts = is_account_locked(identifier)
        
        if is_locked:
            raise serializers.ValidationError({
                "error": f"Account locked due to too many failed login attempts. Please try again after 15 minutes."
            })
        
        # Try to find user by email or username
        user = None
        if '@' in identifier:
            # Login with email
            try:
                user = User.objects.get(email=identifier)
            except User.DoesNotExist:
                pass
        else:
            # Login with username
            try:
                user = User.objects.get(username=identifier)
            except User.DoesNotExist:
                pass
        
        # Check if user exists and password is correct
        if user and user.check_password(password):
            # Reset failed login attempts on successful login
            reset_login_attempts(identifier)
            data['user'] = user
            return data
        else:
            # Increment failed attempts
            new_attempts = increment_login_attempts(identifier)
            remaining = max_attempts - new_attempts
            
            if remaining > 0:
                raise serializers.ValidationError({
                    "error": f"Invalid credentials. {remaining} attempts remaining before account lockout."
                })
            else:
                raise serializers.ValidationError({
                    "error": "Invalid credentials. Account is now locked for 15 minutes."
                })


class SpecializationSerializer(serializers.ModelSerializer):
    """Serializer for Specialization model"""
    class Meta:
        model = Specialization
        fields = ['id', 'name', 'description']
        read_only_fields = ['id']


class CertificateSerializer(serializers.ModelSerializer):
    """Serializer for Certificate model"""
    class Meta:
        model = Certificate
        fields = ['id', 'title', 'issuer', 'issue_date', 'certificate_url']
        read_only_fields = ['id']


class PointsWalletSerializer(serializers.ModelSerializer):
    """Serializer for PointsWallet model"""
    class Meta:
        model = PointsWallet
        fields = ['id', 'balance']
        read_only_fields = ['id', 'balance']


class UserDetailSerializer(serializers.ModelSerializer):
    """
    Detailed user serializer for login response
    Includes specializations, wallet, and profile info
    """
    specializations = SpecializationSerializer(many=True, read_only=True)
    wallet = PointsWalletSerializer(read_only=True)
    profile_image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'phone_number',
            'bio',
            'profile_image_url',
            'specializations',
            'wallet',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'email', 'created_at', 'updated_at']
    
    def get_profile_image_url(self, obj):
        """Get absolute URL for profile image"""
        if obj.profile_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_image.url)
            return obj.profile_image.url
        return None


class ResendOTPSerializer(serializers.Serializer):
    """Serializer for resending OTP"""
    email = serializers.EmailField(required=True)
    
    def validate_email(self, value):
        """Check if there's a pending registration for this email"""
        from django.core.cache import cache
        cache_key = f'pending_registration_{value}'
        registration_data = cache.get(cache_key)
        
        if not registration_data:
            raise serializers.ValidationError(
                "No pending registration found for this email. Please register first."
            )
        
        return value
    
    def create(self, validated_data):
        """Resend OTP to email"""
        email = validated_data['email']
        
        # Get registration data for first name
        from django.core.cache import cache
        cache_key = f'pending_registration_{email}'
        registration_data = cache.get(cache_key)
        first_name = registration_data.get('first_name')
        
        # Send OTP
        success, otp, error_message = send_otp_and_store(email, first_name)
        if not success:
            raise serializers.ValidationError({"error": error_message})
        
        return {
            'email': email,
            'message': 'OTP resent successfully. Please check your email.'
        }