"""
Utility functions for authentication
- OTP generation and validation
- Email sending
- Password validation
"""

import random
import string
from django.core.mail import send_mail
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta


def generate_otp(length=6):
    """
    Generate a random numeric OTP
    
    Args:
        length (int): Length of OTP (default: 6)
    
    Returns:
        str: Generated OTP code
    """
    return ''.join(random.choices(string.digits, k=length))


def store_otp(email, otp, validity_minutes=5):
    """
    Store OTP in Django cache with expiration
    
    Args:
        email (str): User's email address
        otp (str): Generated OTP code
        validity_minutes (int): How long OTP is valid (default: 5 minutes)
    
    Returns:
        bool: True if stored successfully
    """
    cache_key = f'otp_{email}'
    cache.set(cache_key, otp, timeout=validity_minutes * 60)
    return True


def verify_otp(email, otp):
    """
    Verify if the provided OTP matches the stored one
    
    Args:
        email (str): User's email address
        otp (str): OTP code to verify
    
    Returns:
        bool: True if OTP is valid, False otherwise
    """
    cache_key = f'otp_{email}'
    stored_otp = cache.get(cache_key)
    
    if stored_otp and stored_otp == otp:
        # OTP is valid, delete it from cache (one-time use)
        cache.delete(cache_key)
        return True
    
    return False


def can_resend_otp(email):
    """
    Check if user can request a new OTP
    (Rate limiting: 60 seconds between requests)
    
    Args:
        email (str): User's email address
    
    Returns:
        tuple: (can_resend: bool, seconds_remaining: int)
    """
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
    """
    Mark that an OTP was just sent to this email
    (For rate limiting)
    
    Args:
        email (str): User's email address
    """
    cache_key = f'otp_last_sent_{email}'
    cache.set(cache_key, timezone.now(), timeout=300)  # 5 minutes


def get_otp_resend_count(email):
    """
    Get how many times OTP has been resent for this email
    
    Args:
        email (str): User's email address
    
    Returns:
        int: Number of resend attempts
    """
    cache_key = f'otp_resend_count_{email}'
    count = cache.get(cache_key, 0)
    return count


def increment_otp_resend_count(email):
    """
    Increment the OTP resend counter
    
    Args:
        email (str): User's email address
    
    Returns:
        int: New resend count
    """
    cache_key = f'otp_resend_count_{email}'
    count = cache.get(cache_key, 0) + 1
    cache.set(cache_key, count, timeout=300)  # Reset after 5 minutes
    return count


def send_verification_email(email, otp, first_name=None):
    """
    Send OTP verification email to user
    
    Args:
        email (str): Recipient email address
        otp (str): OTP code to send
        first_name (str): User's first name for personalization
    
    Returns:
        bool: True if email sent successfully
    """
    subject = 'Welcome to xBrain! Verify your email'
    
    # Personalized greeting
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
    """
    Generate OTP, store it, and send email
    
    Args:
        email (str): User's email address
        first_name (str): User's first name
    
    Returns:
        tuple: (success: bool, otp: str or None, error_message: str or None)
    """
    # Check if can resend
    can_resend, seconds_remaining = can_resend_otp(email)
    if not can_resend:
        return False, None, f"Please wait {seconds_remaining} seconds before requesting a new code"
    
    # Check resend count
    resend_count = get_otp_resend_count(email)
    max_resends = getattr(settings, 'OTP_MAX_RESEND_ATTEMPTS', 3)
    if resend_count >= max_resends:
        return False, None, "Maximum OTP resend attempts reached. Please try again later."
    
    # Generate and store OTP
    otp = generate_otp(getattr(settings, 'OTP_LENGTH', 6))
    validity = getattr(settings, 'OTP_VALIDITY_MINUTES', 5)
    store_otp(email, otp, validity)
    
    # Send email
    email_sent = send_verification_email(email, otp, first_name)
    if not email_sent:
        return False, None, "Failed to send verification email. Please try again."
    
    # Mark as sent and increment counter
    mark_otp_sent(email)
    increment_otp_resend_count(email)
    
    return True, otp, None


def send_welcome_email(email, first_name=None, username=None):
    """
    Send welcome email after successful account verification
    
    Args:
        email (str): User's email address
        first_name (str): User's first name
        username (str): User's username
    
    Returns:
        bool: True if email sent successfully
    """
    subject = '🎉 Welcome to xBrain! Your account is ready'
    
    # Personalized greeting
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
    """
    Validate password meets security requirements:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number
    - At least one special character
    
    Args:
        password (str): Password to validate
    
    Returns:
        tuple: (is_valid: bool, error_message: str or None)
    """
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
    """
    Get number of failed login attempts for an identifier (email/username)
    
    Args:
        identifier (str): Email or username
    
    Returns:
        int: Number of failed attempts
    """
    cache_key = f'login_attempts_{identifier}'
    return cache.get(cache_key, 0)


def increment_login_attempts(identifier):
    """
    Increment failed login attempts counter
    
    Args:
        identifier (str): Email or username
    
    Returns:
        int: New attempt count
    """
    cache_key = f'login_attempts_{identifier}'
    attempts = cache.get(cache_key, 0) + 1
    lockout_minutes = getattr(settings, 'LOGIN_LOCKOUT_MINUTES', 15)
    cache.set(cache_key, attempts, timeout=lockout_minutes * 60)
    return attempts


def reset_login_attempts(identifier):
    """
    Reset failed login attempts (on successful login)
    
    Args:
        identifier (str): Email or username
    """
    cache_key = f'login_attempts_{identifier}'
    cache.delete(cache_key)


def is_account_locked(identifier):
    """
    Check if account is locked due to too many failed attempts
    
    Args:
        identifier (str): Email or username
    
    Returns:
        tuple: (is_locked: bool, attempts: int, max_attempts: int)
    """
    attempts = get_login_attempts(identifier)
    max_attempts = getattr(settings, 'MAX_LOGIN_ATTEMPTS', 5)
    
    if attempts >= max_attempts:
        return True, attempts, max_attempts
    
    return False, attempts, max_attempts
