from django.test import TestCase, override_settings
from django.urls import reverse
from django.core.cache import cache
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch
from .models import User, Specialization, UserSpecialization, PointsWallet
import uuid


# ============================================================
# REGISTRATION TESTS
# ============================================================
class RegisterTests(TestCase):
    """Tests for POST /api/auth/register/"""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse('api:register')
        self.valid_data = {
            'email': 'newuser@example.com',
            'username': 'newuser123',
            'password': 'SecurePass123!',
            'first_name': 'New',
            'last_name': 'User',
            'phone_number': '+1234567890',
        }
        cache.clear()

    def tearDown(self):
        cache.clear()

    @patch('api.serializers.send_otp_and_store')
    def test_register_success(self, mock_otp):
        """Successful registration stores data in cache and returns 200"""
        mock_otp.return_value = (True, '123456', None)
        response = self.client.post(self.url, self.valid_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('email', response.data)
        self.assertIn('message', response.data)
        self.assertNotIn('otp', response.data)  # OTP must NOT be in response

    @patch('api.serializers.send_otp_and_store')
    def test_register_with_optional_bio(self, mock_otp):
        """Registration with optional bio field"""
        mock_otp.return_value = (True, '123456', None)
        self.valid_data['bio'] = 'I am a developer'
        response = self.client.post(self.url, self.valid_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_register_missing_required_fields(self):
        """Registration fails when required fields are missing"""
        # No email
        data = self.valid_data.copy()
        del data['email']
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

        # No password
        data = self.valid_data.copy()
        del data['password']
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

        # No username
        data = self.valid_data.copy()
        del data['username']
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data)

    def test_register_duplicate_email(self):
        """Registration fails if email is already registered"""
        User.objects.create_user(
            email='newuser@example.com',
            username='existing1',
            password='Test1234!',
        )
        response = self.client.post(self.url, self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_register_duplicate_username(self):
        """Registration fails if username is already taken (case-insensitive)"""
        User.objects.create_user(
            email='other@example.com',
            username='newuser123',
            password='Test1234!',
        )
        response = self.client.post(self.url, self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data)

    def test_register_duplicate_phone(self):
        """Registration fails if phone number is already registered"""
        User.objects.create_user(
            email='other@example.com',
            username='otheruser1',
            password='Test1234!',
            phone_number='+1234567890',
        )
        response = self.client.post(self.url, self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('phone_number', response.data)

    def test_register_weak_password_no_uppercase(self):
        """Registration fails with password missing uppercase"""
        self.valid_data['password'] = 'weakpass123!'
        response = self.client.post(self.url, self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_register_weak_password_no_number(self):
        """Registration fails with password missing number"""
        self.valid_data['password'] = 'WeakPassword!'
        response = self.client.post(self.url, self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_register_weak_password_no_special_char(self):
        """Registration fails with password missing special character"""
        self.valid_data['password'] = 'WeakPass123'
        response = self.client.post(self.url, self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_register_weak_password_too_short(self):
        """Registration fails with password shorter than 8 characters"""
        self.valid_data['password'] = 'Aa1!'
        response = self.client.post(self.url, self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_register_invalid_email_format(self):
        """Registration fails with invalid email format"""
        self.valid_data['email'] = 'not-an-email'
        response = self.client.post(self.url, self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_register_username_too_short(self):
        """Registration fails with username shorter than 8 chars"""
        self.valid_data['username'] = 'abc'
        response = self.client.post(self.url, self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data)

    def test_register_username_too_long(self):
        """Registration fails with username longer than 16 chars"""
        self.valid_data['username'] = 'a' * 17
        response = self.client.post(self.url, self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data)

    def test_register_username_starts_with_number(self):
        """Registration fails when username starts with a number"""
        self.valid_data['username'] = '1baduser1'
        response = self.client.post(self.url, self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data)

    def test_register_invalid_phone_number(self):
        """Registration fails with invalid phone number format"""
        self.valid_data['phone_number'] = '123'
        response = self.client.post(self.url, self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('phone_number', response.data)

    @patch('api.serializers.send_otp_and_store')
    def test_register_pending_email_blocked(self, mock_otp):
        """Registration fails if an OTP was already sent to this email (still pending)"""
        mock_otp.return_value = (True, '123456', None)
        # First registration
        self.client.post(self.url, self.valid_data, format='json')
        # Second attempt with same email
        response = self.client.post(self.url, self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_register_empty_body(self):
        """Registration fails with empty request body"""
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ============================================================
# VERIFY EMAIL TESTS
# ============================================================
class VerifyEmailTests(TestCase):
    """Tests for POST /api/auth/verify-email/"""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse('api:verify-email')
        self.email = 'verify@example.com'
        self.registration_data = {
            'email': self.email,
            'username': 'verifyuser',
            'password': 'SecurePass123!',
            'first_name': 'Verify',
            'last_name': 'User',
            'phone_number': '+9876543210',
            'bio': '',
        }
        cache.clear()

    def tearDown(self):
        cache.clear()

    def _setup_pending_registration(self, otp='123456'):
        """Helper: simulate a pending registration with OTP in cache"""
        cache.set(f'pending_registration_{self.email}', self.registration_data, timeout=600)
        cache.set(f'otp_{self.email}', otp, timeout=300)

    def test_verify_email_success(self):
        """Successful OTP verification creates user and returns tokens"""
        self._setup_pending_registration('123456')
        response = self.client.post(self.url, {
            'email': self.email,
            'otp': '123456'
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('access_token', response.data)
        self.assertIn('refresh_token', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['email'], self.email)

        # User actually exists in DB
        self.assertTrue(User.objects.filter(email=self.email).exists())

    def test_verify_email_creates_wallet(self):
        """Wallet is auto-created when user is verified"""
        self._setup_pending_registration('123456')
        response = self.client.post(self.url, {
            'email': self.email,
            'otp': '123456'
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email=self.email)
        self.assertTrue(PointsWallet.objects.filter(user=user).exists())
        self.assertEqual(user.wallet.balance, 0)

    def test_verify_email_wrong_otp(self):
        """Verification fails with wrong OTP"""
        self._setup_pending_registration('123456')
        response = self.client.post(self.url, {
            'email': self.email,
            'otp': '000000'
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(email=self.email).exists())

    def test_verify_email_expired_otp(self):
        """Verification fails when OTP has expired (not in cache)"""
        # Set up registration data but no OTP
        cache.set(f'pending_registration_{self.email}', self.registration_data, timeout=600)
        # Don't set OTP — simulates expired

        response = self.client.post(self.url, {
            'email': self.email,
            'otp': '123456'
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_email_no_pending_registration(self):
        """Verification fails when no registration data exists"""
        cache.set(f'otp_{self.email}', '123456', timeout=300)
        # No pending registration data

        response = self.client.post(self.url, {
            'email': self.email,
            'otp': '123456'
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_email_missing_fields(self):
        """Verification fails when email or otp is missing"""
        response = self.client.post(self.url, {'email': self.email}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.post(self.url, {'otp': '123456'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_email_otp_too_short(self):
        """Verification fails when OTP is less than 6 digits"""
        response = self.client.post(self.url, {
            'email': self.email,
            'otp': '123'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_email_cleans_up_cache(self):
        """After successful verification, pending data and OTP are removed from cache"""
        self._setup_pending_registration('123456')
        self.client.post(self.url, {
            'email': self.email,
            'otp': '123456'
        }, format='json')

        self.assertIsNone(cache.get(f'pending_registration_{self.email}'))
        self.assertIsNone(cache.get(f'otp_{self.email}'))


# ============================================================
# LOGIN TESTS
# ============================================================
class LoginTests(TestCase):
    """Tests for POST /api/auth/login/"""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse('api:login')
        self.password = 'SecurePass123!'
        self.user = User.objects.create_user(
            email='login@example.com',
            username='loginuser',
            password=self.password,
            first_name='Login',
            last_name='User',
        )
        PointsWallet.objects.get_or_create(user=self.user)
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_login_with_email_success(self):
        """Login with valid email and password returns tokens and user"""
        response = self.client.post(self.url, {
            'identifier': 'login@example.com',
            'password': self.password,
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', response.data)
        self.assertIn('refresh_token', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['email'], 'login@example.com')

    def test_login_with_username_success(self):
        """Login with valid username and password returns tokens and user"""
        response = self.client.post(self.url, {
            'identifier': 'loginuser',
            'password': self.password,
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', response.data)

    def test_login_wrong_password(self):
        """Login fails with wrong password and shows remaining attempts"""
        response = self.client.post(self.url, {
            'identifier': 'login@example.com',
            'password': 'WrongPass123!',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIn('remaining', str(response.data['error']))

    def test_login_nonexistent_user(self):
        """Login fails for a user that doesn't exist"""
        response = self.client.post(self.url, {
            'identifier': 'nobody@example.com',
            'password': 'SomePass123!',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_missing_fields(self):
        """Login fails when identifier or password is missing"""
        response = self.client.post(self.url, {
            'identifier': 'login@example.com',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.post(self.url, {
            'password': self.password,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_case_insensitive_email(self):
        """Login works with different email casing"""
        response = self.client.post(self.url, {
            'identifier': 'LOGIN@EXAMPLE.COM',
            'password': self.password,
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_login_account_lockout_after_max_attempts(self):
        """Account locks after 5 failed login attempts"""
        for i in range(5):
            self.client.post(self.url, {
                'identifier': 'login@example.com',
                'password': 'WrongPass123!',
            }, format='json')

        # 6th attempt should say locked
        response = self.client.post(self.url, {
            'identifier': 'login@example.com',
            'password': 'WrongPass123!',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('locked', str(response.data['error']).lower())

    def test_login_lockout_blocks_correct_password(self):
        """Even correct password is rejected when account is locked"""
        for i in range(5):
            self.client.post(self.url, {
                'identifier': 'login@example.com',
                'password': 'WrongPass123!',
            }, format='json')

        response = self.client.post(self.url, {
            'identifier': 'login@example.com',
            'password': self.password,  # correct password
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('locked', str(response.data['error']).lower())

    def test_login_attempts_reset_on_success(self):
        """Failed attempt counter resets after a successful login"""
        # 3 failed attempts
        for i in range(3):
            self.client.post(self.url, {
                'identifier': 'login@example.com',
                'password': 'WrongPass123!',
            }, format='json')

        # Successful login
        response = self.client.post(self.url, {
            'identifier': 'login@example.com',
            'password': self.password,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Another failed attempt should show 4 remaining (reset happened)
        response = self.client.post(self.url, {
            'identifier': 'login@example.com',
            'password': 'WrongPass123!',
        }, format='json')
        self.assertIn('4', str(response.data['error']))

    def test_login_returns_user_wallet(self):
        """Login response includes wallet data"""
        response = self.client.post(self.url, {
            'identifier': 'login@example.com',
            'password': self.password,
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('wallet', response.data['user'])
        self.assertEqual(response.data['user']['wallet']['balance'], 0)

    def test_login_returns_specializations(self):
        """Login response includes specializations (empty initially)"""
        response = self.client.post(self.url, {
            'identifier': 'login@example.com',
            'password': self.password,
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('specializations', response.data['user'])
        self.assertEqual(response.data['user']['specializations'], [])


# ============================================================
# RESEND OTP TESTS
# ============================================================
class ResendOTPTests(TestCase):
    """Tests for POST /api/auth/resend-otp/"""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse('api:resend-otp')
        self.email = 'resend@example.com'
        self.registration_data = {
            'email': self.email,
            'username': 'resenduser',
            'password': 'SecurePass123!',
            'first_name': 'Resend',
            'last_name': 'User',
            'phone_number': '+1112223333',
            'bio': '',
        }
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_resend_otp_no_pending_registration(self):
        """Resend fails when there's no pending registration"""
        response = self.client.post(self.url, {
            'email': self.email,
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_resend_otp_missing_email(self):
        """Resend fails when email is not provided"""
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ============================================================
# REFRESH TOKEN TESTS
# ============================================================
class RefreshTokenTests(TestCase):
    """Tests for POST /api/auth/token/refresh/"""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse('api:token-refresh')
        self.user = User.objects.create_user(
            email='refresh@example.com',
            username='refreshuser',
            password='SecurePass123!',
        )
        PointsWallet.objects.get_or_create(user=self.user)

    def test_refresh_token_success(self):
        """Valid refresh token returns new access and refresh tokens"""
        # Login first to get tokens
        login_url = reverse('api:login')
        login_response = self.client.post(login_url, {
            'identifier': 'refresh@example.com',
            'password': 'SecurePass123!',
        }, format='json')
        refresh_token = login_response.data['refresh_token']

        # Use refresh token
        response = self.client.post(self.url, {
            'refresh': refresh_token,
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_refresh_token_invalid(self):
        """Invalid refresh token returns 401"""
        response = self.client.post(self.url, {
            'refresh': 'invalid.token.here',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_token_missing(self):
        """Missing refresh token returns 400"""
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ============================================================
# USER PROFILE TESTS
# ============================================================
class UserProfileTests(TestCase):
    """Tests for GET /api/users/me/"""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse('api:user-profile')
        self.user = User.objects.create_user(
            email='profile@example.com',
            username='profileuser',
            password='SecurePass123!',
            first_name='Profile',
            last_name='User',
            phone_number='+5556667777',
            bio='My bio',
        )
        PointsWallet.objects.get_or_create(user=self.user)

    def test_get_profile_authenticated(self):
        """Authenticated user can get their full profile"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'profile@example.com')
        self.assertEqual(response.data['username'], 'profileuser')
        self.assertEqual(response.data['first_name'], 'Profile')
        self.assertEqual(response.data['last_name'], 'User')
        self.assertEqual(response.data['bio'], 'My bio')
        self.assertIn('wallet', response.data)
        self.assertIn('specializations', response.data)
        self.assertIn('created_at', response.data)
        self.assertIn('updated_at', response.data)

    def test_get_profile_unauthenticated(self):
        """Unauthenticated request returns 401"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_profile_invalid_token(self):
        """Request with invalid token returns 401"""
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalid.token.here')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_does_not_expose_password(self):
        """Profile response never includes the password field"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('password', response.data)


# ============================================================
# SPECIALIZATION TESTS
# ============================================================
class SpecializationListTests(TestCase):
    """Tests for GET /api/specializations/"""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse('api:specializations')
        self.user = User.objects.create_user(
            email='spec@example.com',
            username='specuser1',
            password='SecurePass123!',
        )
        self.spec1 = Specialization.objects.create(name='Backend Development', description='Server-side')
        self.spec2 = Specialization.objects.create(name='Frontend Development', description='Client-side')
        self.spec3 = Specialization.objects.create(name='Machine Learning', description='AI and ML')

    def test_get_specializations_list(self):
        """Returns all specializations with count"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(len(response.data['results']), 3)

    def test_get_specializations_empty(self):
        """Returns message when no specializations exist"""
        Specialization.objects.all().delete()
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertEqual(response.data['results'], [])

    def test_get_specializations_unauthenticated(self):
        """Unauthenticated request returns 401"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ============================================================
# USER SPECIALIZATION TESTS
# ============================================================
class UserSpecializationTests(TestCase):
    """Tests for GET/PUT/PATCH /api/users/me/specializations/"""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse('api:user-specializations')
        self.user = User.objects.create_user(
            email='userspec@example.com',
            username='userspec1',
            password='SecurePass123!',
            first_name='Test',
            last_name='User',
        )
        self.spec1 = Specialization.objects.create(name='Backend Development', description='Server-side')
        self.spec2 = Specialization.objects.create(name='Frontend Development', description='Client-side')
        self.spec3 = Specialization.objects.create(name='Machine Learning', description='AI and ML')

    def test_get_user_specializations_initially_empty(self):
        """New user has no specializations and form_completed_at is null"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data['specialization_form_completed_at'])
        self.assertEqual(response.data['specializations'], [])

    def test_set_user_specializations(self):
        """PUT replaces all specializations and sets form_completed_at"""
        self.client.force_authenticate(user=self.user)
        data = {'specialization_ids': [str(self.spec1.id), str(self.spec2.id)]}
        response = self.client.put(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data['specialization_form_completed_at'])
        self.assertEqual(len(response.data['specializations']), 2)
        self.assertEqual(self.user.specializations.count(), 2)

    def test_replace_user_specializations(self):
        """PUT replaces existing specializations with new ones"""
        UserSpecialization.objects.create(user=self.user, specialization=self.spec1)
        self.client.force_authenticate(user=self.user)

        data = {'specialization_ids': [str(self.spec2.id), str(self.spec3.id)]}
        response = self.client.put(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['specializations']), 2)
        spec_ids = [s['id'] for s in response.data['specializations']]
        self.assertNotIn(str(self.spec1.id), spec_ids)

    def test_set_empty_specializations(self):
        """PUT with empty list clears all specializations"""
        UserSpecialization.objects.create(user=self.user, specialization=self.spec1)
        self.client.force_authenticate(user=self.user)

        data = {'specialization_ids': []}
        response = self.client.put(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['specializations'], [])
        self.assertEqual(self.user.specializations.count(), 0)

    def test_set_invalid_specialization_id(self):
        """PUT fails with a non-existent specialization ID"""
        self.client.force_authenticate(user=self.user)
        fake_id = str(uuid.uuid4())
        data = {'specialization_ids': [fake_id]}
        response = self.client.put(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_skip_specialization_form(self):
        """PATCH with skip=true marks form as completed with no specializations"""
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(self.url, {'skip': True}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data['specialization_form_completed_at'])
        self.assertEqual(response.data['specializations'], [])
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.specialization_form_completed_at)

    def test_skip_then_add_specializations(self):
        """User can add specializations after skipping the form"""
        self.client.force_authenticate(user=self.user)
        self.client.patch(self.url, {'skip': True}, format='json')

        data = {'specialization_ids': [str(self.spec1.id)]}
        response = self.client.put(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['specializations']), 1)

    def test_unauthenticated_access(self):
        """Unauthenticated requests return 401"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        response = self.client.put(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_duplicate_specialization_in_request(self):
        """Sending the same specialization ID twice is handled gracefully"""
        self.client.force_authenticate(user=self.user)
        data = {'specialization_ids': [str(self.spec1.id), str(self.spec1.id)]}
        response = self.client.put(self.url, data, format='json')

        # Should either succeed with 1 entry or return 400
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST])
