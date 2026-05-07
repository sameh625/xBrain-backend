import secrets
import string
from django.core.mail import send_mail
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta


def generate_otp(length=6):
    return ''.join(secrets.choice(string.digits) for _ in range(length))


def store_otp(email, otp, validity_minutes=5):
    cache_key = f'otp_{email}'
    cache.set(cache_key, otp, timeout=validity_minutes * 60)
    return True


ATTACHMENT_LIMITS = {
    'image': {
        'mime_types': ['image/jpeg', 'image/png', 'image/webp'],
        'max_bytes': 5 * 1024 * 1024,  # 5 MB
    },
    'video': {
        'mime_types': ['video/mp4', 'video/quicktime'],
        'max_bytes': 50 * 1024 * 1024,  # 50 MB
    },
    'audio': {
        'mime_types': [
            'audio/mpeg',   # MP3
            'audio/mp4',    # M4A / AAC (iPhone voice memos)
            'audio/aac',    # AAC alternate MIME
            'audio/ogg',    # OGG
            'audio/webm',   # WebM audio
        ],
        'max_bytes': 15 * 1024 * 1024,  # 15 MB ≈ 15-20 min compressed audio
    },
    'pdf': {
        'mime_types': ['application/pdf'],
        'max_bytes': 10 * 1024 * 1024,  # 10 MB
    },
}

MAX_ATTACHMENTS_PER_PARENT = 4


def classify_and_validate_attachment(uploaded_file):
    """Classify an uploaded file by MIME type and validate its size.

    Returns the tuple (kind, mime_type) where kind is one of 'image', 'video',
    'audio', 'pdf'. Raises rest_framework.exceptions.ValidationError with a
    user-friendly message if the file is too large or has an unsupported type.
    """
    from rest_framework.exceptions import ValidationError as DRFValidationError

    mime = (uploaded_file.content_type or '').lower()
    for kind, limits in ATTACHMENT_LIMITS.items():
        if mime in limits['mime_types']:
            if uploaded_file.size > limits['max_bytes']:
                max_mb = limits['max_bytes'] // (1024 * 1024)
                raise DRFValidationError(
                    f'{kind.capitalize()} too large (max {max_mb} MB).'
                )
            return kind, mime
    raise DRFValidationError(
        f'Unsupported file type: {mime or "unknown"}. '
        f'Allowed: image (jpeg/png/webp), video (mp4/quicktime), '
        f'audio (mpeg/mp4/aac/ogg/webm), pdf.'
    )


def verify_otp(email, otp, consume=True):
    """Verify the OTP for an email. By default, consumes (deletes) the OTP on success."""
    cache_key = f'otp_{email}'
    stored_otp = cache.get(cache_key)

    if stored_otp and stored_otp == otp:
        if consume:
            cache.delete(cache_key)
        return True

    return False


def can_resend_otp(email):
    cache_key = f'otp_last_sent_{email}'
    last_sent = cache.get(cache_key)
    
    if last_sent is None:
        return True, 0
    
    elapsed = (timezone.now() - last_sent).total_seconds()
    delay_seconds = getattr(settings, 'OTP_RESEND_DELAY_SECONDS', 60)
    
    if elapsed >= delay_seconds:
        return True, 0
    else:
        return False, int(delay_seconds - elapsed)


def mark_otp_sent(email):
    cache_key = f'otp_last_sent_{email}'
    cache.set(cache_key, timezone.now(), timeout=300)  # 5 minutes


def get_otp_resend_count(email):
    cache_key = f'otp_resend_count_{email}'
    count = cache.get(cache_key, 0)
    return count


def increment_otp_resend_count(email):
    cache_key = f'otp_resend_count_{email}'
    count = cache.get(cache_key, 0) + 1
    cache.set(cache_key, count, timeout=300)
    return count


def send_verification_email(email, otp, first_name=None):
    subject = 'Welcome to xBrain! Verify your email'
    
    greeting = f"Hi {first_name}," if first_name else "Hi,"
    
    message = f"""{greeting}

Thank you for joining xBrain!

Your verification code is: {otp}

This code will expire in 5 minutes.

If you didn't create an account, please ignore this email.

Best regards,
The xBrain Team
"""
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


def send_otp_and_store(email, first_name=None):
    can_resend, seconds_remaining = can_resend_otp(email)
    if not can_resend:
        return False, None, f"Please wait {seconds_remaining} seconds before requesting a new code"
    
    resend_count = get_otp_resend_count(email)
    max_resends = getattr(settings, 'OTP_MAX_RESEND_ATTEMPTS', 3)
    if resend_count >= max_resends:
        return False, None, "Maximum OTP resend attempts reached. Please try again later."
    
    otp = generate_otp(getattr(settings, 'OTP_LENGTH', 6))
    validity = getattr(settings, 'OTP_VALIDITY_MINUTES', 5)
    store_otp(email, otp, validity)
    
    # Try to send email, but don't fail if it can't be sent
    email_sent = send_verification_email(email, otp, first_name)
    if not email_sent:
        print(f"[WARNING] Email could not be sent to {email}. OTP is stored and returned in response.")
    
    mark_otp_sent(email)
    increment_otp_resend_count(email)
    
    return True, otp, None


def send_welcome_email(email, first_name=None, username=None):
    subject = '🎉 Welcome to xBrain! Your account is ready'
    
    greeting = f"Hi {first_name}," if first_name else "Hi,"
    username_text = f"Your username: **{username}**" if username else ""
    
    message = f"""{greeting}

Congratulations! Your xBrain account has been successfully verified and is now active.

{username_text}

You can now:
✅ Log in to your account
✅ Explore specializations
✅ Build your professional profile
✅ Earn points and badges

Start exploring xBrain today!

If you have any questions, feel free to reach out to our support team.

Best regards,
The xBrain Team

---
© 2026 xBrain. All rights reserved.
"""
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error sending welcome email: {e}")
        return False


def validate_password_strength(password):
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"
    
    special_characters = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if not any(c in special_characters for c in password):
        return False, "Password must contain at least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)"
    
    return True, None


def get_login_attempts(identifier):
    cache_key = f'login_attempts_{identifier}'
    return cache.get(cache_key, 0)


def increment_login_attempts(identifier):
    cache_key = f'login_attempts_{identifier}'
    attempts = cache.get(cache_key, 0) + 1
    lockout_minutes = getattr(settings, 'LOGIN_LOCKOUT_MINUTES', 15)
    cache.set(cache_key, attempts, timeout=lockout_minutes * 60)
    return attempts


def reset_login_attempts(identifier):
    cache_key = f'login_attempts_{identifier}'
    cache.delete(cache_key)


def is_account_locked(identifier):
    attempts = get_login_attempts(identifier)
    max_attempts = getattr(settings, 'MAX_LOGIN_ATTEMPTS', 5)
    
    if attempts >= max_attempts:
        return True, attempts, max_attempts
    
    return False, attempts, max_attempts


def send_password_reset_email(email, otp, first_name=None):
    subject = 'Password Reset Request - xBrain'
    
    greeting = f"Hi {first_name}," if first_name else "Hi,"
    
    message = f"""{greeting}

We received a request to reset your password for your xBrain account.

Your password reset code is: {otp}

This code will expire in 10 minutes.

If you didn't request a password reset, please ignore this email. Your password will remain unchanged.

Best regards,
The xBrain Team
"""
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error sending password reset email: {e}")
        return False


def send_reset_otp_and_store(email, first_name=None):
    otp = generate_otp(getattr(settings, 'OTP_LENGTH', 6))
    validity = 10  # 10 minutes validity for reset OTP
    
    cache_key = f'reset_otp_{email}'
    cache.set(cache_key, otp, timeout=validity * 60)
    
    email_sent = send_password_reset_email(email, otp, first_name)
    if not email_sent:
        print(f"[WARNING] Reset Email could not be sent to {email}.")
    
    return True, otp, None
