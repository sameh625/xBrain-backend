from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password as django_validate_password
from django.core.exceptions import ValidationError
from .models import User, Specialization, Certificate, PointsWallet
from .utils import validate_password_strength, send_otp_and_store, verify_otp


class UserRegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    username = serializers.CharField(required=True, min_length=8, max_length=16)
    password = serializers.CharField(required=True, write_only=True, min_length=8)
    first_name = serializers.CharField(required=True, max_length=50)
    last_name = serializers.CharField(required=True, max_length=50)
    phone_number = serializers.CharField(required=True, max_length=15)
    bio = serializers.CharField(required=False, allow_blank=True, max_length=500)
    profile_image = serializers.ImageField(required=False, allow_null=True)
    
    def validate_email(self, value):
        from django.core.cache import cache
        if cache.get(f'pending_registration_{value}'):
            raise serializers.ValidationError("An OTP has already been sent to this email. Please verify or wait before requesting another.")
        
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already registered.")
        
        return value.lower()
    
    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        
        if not value[0].isalpha():
            raise serializers.ValidationError("Username must start with a letter.")
        
        import re
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9._-]*$', value):
            raise serializers.ValidationError("Username can only contain letters, numbers, dots, underscores, and hyphens.")
        
        return value.lower()
    
    def validate_password(self, value):
        is_valid, error_message = validate_password_strength(value)
        if not is_valid:
            raise serializers.ValidationError(error_message)
        return value
    
    def validate_phone_number(self, value):
        import re
        if not re.match(r'^\+?[1-9]\d{7,14}$', value):
            raise serializers.ValidationError(
                "Enter a valid phone number (7-15 digits, optional + prefix)."
            )
        
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("This phone number is already registered.")
        
        return value
    
    def create(self, validated_data):
        email = validated_data['email']
        first_name = validated_data['first_name']
        
        from django.core.cache import cache
        cache_key = f'pending_registration_{email}'
        cache.set(cache_key, validated_data, timeout=600)
        
        success, otp, error_message = send_otp_and_store(email, first_name)
        if not success:
            raise serializers.ValidationError({"otp": error_message})
        
        return {
            'email': email,
            'otp': otp,
            'message': 'OTP sent successfully. Please check your email.'
        }


class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    otp = serializers.CharField(required=True, min_length=6, max_length=6)
    
    def validate(self, data):
        email = data['email']
        otp = data['otp']
        
        if not verify_otp(email, otp):
            raise serializers.ValidationError({"otp": "Invalid or expired OTP code."})
        
        from django.core.cache import cache
        cache_key = f'pending_registration_{email}'
        registration_data = cache.get(cache_key)
        
        if not registration_data:
            raise serializers.ValidationError({"email": "Registration data not found. Please register again."})
        
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
            
            if 'profile_image' in registration_data and registration_data['profile_image']:
                user.profile_image = registration_data['profile_image']
                user.save()
            
            cache.delete(cache_key)
            
            cache.delete(f'otp_resend_count_{email}')
            cache.delete(f'otp_last_sent_{email}')
            
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
    identifier = serializers.CharField(required=True, help_text="Email or Username")
    password = serializers.CharField(required=True, write_only=True)
    
    def validate(self, data):
        identifier = data['identifier'].lower()
        password = data['password']
        
        from .utils import is_account_locked, increment_login_attempts, reset_login_attempts
        is_locked, attempts, max_attempts = is_account_locked(identifier)
        
        if is_locked:
            raise serializers.ValidationError({
                "error": f"Account locked due to too many failed login attempts. Please try again after 15 minutes."
            })
        
        user = None
        if '@' in identifier:
            try:
                user = User.objects.get(email=identifier)
            except User.DoesNotExist:
                pass
        else:
            try:
                user = User.objects.get(username=identifier)
            except User.DoesNotExist:
                pass
        
        if user and user.check_password(password):
            reset_login_attempts(identifier)
            data['user'] = user
            return data
        else:
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
    class Meta:
        model = Specialization
        fields = ['id', 'name', 'description']
        read_only_fields = ['id']


class CertificateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Certificate
        fields = ['id', 'title', 'issuer', 'issue_date', 'certificate_url']
        read_only_fields = ['id']


class PointsWalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = PointsWallet
        fields = ['id', 'balance']
        read_only_fields = ['id', 'balance']


class UserDetailSerializer(serializers.ModelSerializer):
    specializations = SpecializationSerializer(many=True, read_only=True)
    wallet = PointsWalletSerializer(read_only=True)
    profile_image_url = serializers.SerializerMethodField()
    specialization_form_completed_at = serializers.DateTimeField(read_only=True)

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
            'specialization_form_completed_at',
            'wallet',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'email', 'created_at', 'updated_at', 'specialization_form_completed_at']
    
    def get_profile_image_url(self, obj):
        if obj.profile_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_image.url)
            return obj.profile_image.url
        return None


class ResendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        from django.core.cache import cache
        cache_key = f'pending_registration_{value}'
        registration_data = cache.get(cache_key)

        if not registration_data:
            raise serializers.ValidationError(
                "No pending registration found for this email. Please register first."
            )

        return value

    def create(self, validated_data):
        email = validated_data['email']

        from django.core.cache import cache
        cache_key = f'pending_registration_{email}'
        registration_data = cache.get(cache_key)
        first_name = registration_data.get('first_name')

        success, otp, error_message = send_otp_and_store(email, first_name)
        if not success:
            raise serializers.ValidationError({"error": error_message})

        return {
            'email': email,
            'message': 'OTP resent successfully. Please check your email.'
        }


class UserSpecializationSerializer(serializers.Serializer):
    specialization_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=True,
        required=False,
        help_text="List of specialization UUIDs to assign to user"
    )
    skip = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Set to true to skip the specialization form"
    )

    def validate_specialization_ids(self, value):
        if not value:
            return value

        existing_ids = set(Specialization.objects.filter(
            id__in=value
        ).values_list('id', flat=True))

        invalid_ids = set(str(vid) for vid in value) - set(str(eid) for eid in existing_ids)

        if invalid_ids:
            raise serializers.ValidationError(
                f"Invalid specialization IDs: {', '.join(invalid_ids)}"
            )

        return value

    def validate(self, data):
        if 'specialization_ids' not in data and not data.get('skip'):
            raise serializers.ValidationError(
                "Either 'specialization_ids' or 'skip' must be provided."
            )
        return data