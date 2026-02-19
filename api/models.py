import uuid
import re
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import RegexValidator, MinLengthValidator, MaxLengthValidator, URLValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_username(value):
    if not re.match(r'^[a-zA-Z]', value):
        raise ValidationError(
            _('Username must start with a letter.'),
            code='invalid_username_start'
        )
    
    if not re.match(r'^[a-zA-Z][a-zA-Z0-9._-]*$', value):
        raise ValidationError(
            _('Username can only contain letters, numbers, dots, underscores, and hyphens.'),
            code='invalid_username_format'
        )


def validate_phone_number(value):
    if not re.match(r'^\+?[1-9]\d{7,14}$', value):
        raise ValidationError(
            _('Enter a valid phone number (7-15 digits, optional + prefix).'),
            code='invalid_phone'
        )


class CustomUserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError(_('The Email field must be set'))
        if not username:
            raise ValueError(_('The Username field must be set'))
        
        email = self.normalize_email(email)
        username = username.lower()
        
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        
        return user
    
    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        
        return self.create_user(email, username, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for the user"
    )
    
    email = models.EmailField(
        _('email address'),
        unique=True,
        max_length=255,
        db_index=True,
        help_text="User's email address (used for login)"
    )
    
    username = models.CharField(
        _('username'),
        max_length=16,
        unique=True,
        db_index=True,
        validators=[
            MinLengthValidator(8, message="Username must be at least 8 characters long"),
            MaxLengthValidator(16, message="Username must not exceed 16 characters"),
            validate_username
        ],
        help_text="Unique username (8-16 chars, must start with letter, case-insensitive)"
    )
    
    password = models.CharField(
        _('password'),
        max_length=128,
        help_text="Hashed password"
    )
    
    first_name = models.CharField(
        _('first name'),
        max_length=50,
        blank=True,
        help_text="User's first name"
    )
    
    last_name = models.CharField(
        _('last name'),
        max_length=50,
        blank=True,
        help_text="User's last name"
    )
    
    phone_number = models.CharField(
        _('phone number'),
        max_length=15,
        unique=True,
        blank=True,
        null=True,
        validators=[validate_phone_number],
        help_text="User's phone number (7-15 digits)"
    )
    
    bio = models.TextField(
        _('biography'),
        blank=True,
        max_length=500,
        help_text="User's biography or description"
    )
    
    profile_image = models.ImageField(
        _('profile image'),
        upload_to='profile_images/',
        blank=True,
        null=True,
        help_text="User's profile image"
    )
    
    specializations = models.ManyToManyField(
        'Specialization',
        through='UserSpecialization',
        related_name='users',
        blank=True,
        help_text="User's areas of expertise"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="When the user account was created"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When the user account was last updated"
    )
    
    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text="Designates whether the user can log into the admin site"
    )
    
    is_superuser = models.BooleanField(
        _('superuser status'),
        default=False,
        help_text="Designates that this user has all permissions"
    )

    specialization_form_completed_at = models.DateTimeField(
        _('specialization form completed at'),
        null=True,
        blank=True,
        db_index=True,
        help_text="When the user completed or skipped the specialization form (null = not yet shown)"
    )

    objects = CustomUserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        db_table = 'users'
        verbose_name = _('user')
        verbose_name_plural = _('users')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email'], name='idx_user_email'),
            models.Index(fields=['username'], name='idx_user_username'),
            models.Index(fields=['created_at'], name='idx_user_created'),
        ]
    
    def __str__(self):
        return f"{self.username} ({self.email})"
    
    def save(self, *args, **kwargs):
        self.username = self.username.lower()
        super().save(*args, **kwargs)
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username
    
    def get_short_name(self):
        return self.first_name or self.username


class Specialization(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for the specialization"
    )
    
    name = models.CharField(
        _('name'),
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Name of the specialization (e.g., 'Backend Development')"
    )
    
    description = models.TextField(
        _('description'),
        blank=True,
        max_length=500,
        help_text="Detailed description of the specialization"
    )
    
    class Meta:
        db_table = 'specializations'
        verbose_name = _('specialization')
        verbose_name_plural = _('specializations')
        ordering = ['name']
        indexes = [
            models.Index(fields=['name'], name='idx_spec_name'),
        ]
    
    def __str__(self):
        return self.name


class UserSpecialization(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for this user-specialization relationship"
    )
    
    user = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='user_specializations',
        help_text="User who has this specialization"
    )
    
    specialization = models.ForeignKey(
        'Specialization',
        on_delete=models.CASCADE,
        related_name='specialization_users',
        help_text="Specialization that the user has"
    )
    
    class Meta:
        db_table = 'user_specializations'
        verbose_name = _('user specialization')
        verbose_name_plural = _('user specializations')
        unique_together = ['user', 'specialization']
        indexes = [
            models.Index(fields=['user', 'specialization'], name='idx_user_spec'),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.specialization.name}"


class PointsWallet(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for the wallet"
    )
    
    user = models.OneToOneField(
        'User',
        on_delete=models.CASCADE,
        related_name='wallet',
        db_index=True,
        help_text="User who owns this wallet"
    )
    
    balance = models.PositiveIntegerField(
        _('balance'),
        default=0,
        help_text="Current points balance (cannot be negative)"
    )
    
    class Meta:
        db_table = 'points_wallets'
        verbose_name = _('points wallet')
        verbose_name_plural = _('points wallets')
        indexes = [
            models.Index(fields=['user'], name='idx_wallet_user'),
        ]
    
    def __str__(self):
        return f"{self.user.username}'s Wallet - Balance: {self.balance}"
    
    def add_points(self, amount):
        if amount <= 0:
            raise ValueError("Amount must be positive")
        self.balance += amount
        self.save()
    
    def deduct_points(self, amount):
        if amount <= 0:
            raise ValueError("Amount must be positive")
        if amount > self.balance:
            raise ValueError("Insufficient balance")
        self.balance -= amount
        self.save()


class Certificate(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for the certificate"
    )
    
    user = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='certificates',
        db_index=True,
        help_text="User who owns this certificate"
    )
    
    title = models.CharField(
        _('title'),
        max_length=200,
        help_text="Certificate name/title"
    )
    
    issuer = models.CharField(
        _('issuer'),
        max_length=200,
        help_text="Organization that issued the certificate"
    )
    
    issue_date = models.DateField(
        _('issue date'),
        help_text="When the certificate was issued"
    )
    
    certificate_url = models.URLField(
        _('certificate URL'),
        max_length=500,
        validators=[URLValidator()],
        help_text="URL link to the certificate (external link)"
    )
    
    class Meta:
        db_table = 'certificates'
        verbose_name = _('certificate')
        verbose_name_plural = _('certificates')
        ordering = ['-issue_date']
        indexes = [
            models.Index(fields=['user'], name='idx_cert_user'),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"