from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.core.cache import cache
from .models import User
from unittest.mock import patch

class ForgotPasswordTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='resetuser@example.com',
            username='resetuser',
            password='OldPassword123!',
            first_name='Reset',
            last_name='User',
            phone_number='+1112223334'
        )
        cache.clear()

    def tearDown(self):
        cache.clear()

    @patch('api.utils.send_mail')
    def test_full_password_reset_flow(self, mock_send_mail):
        mock_send_mail.return_value = 1
        
        # Step 1: Forgot Password
        url_forgot = reverse('api:forgot-password')
        response = self.client.post(url_forgot, {'email': self.user.email}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('Password reset code', response.data['message'])
        
        # Get OTP from cache
        otp = cache.get(f'reset_otp_{self.user.email}')
        self.assertIsNotNone(otp)
        
        # Step 2: Verify Reset OTP
        url_verify = reverse('api:verify-reset-otp')
        response = self.client.post(url_verify, {'email': self.user.email, 'otp': otp}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('reset_token', response.data)
        
        reset_token = response.data['reset_token']
        
        # Step 3: Reset Password
        url_reset = reverse('api:reset-password')
        data = {
            'email': self.user.email,
            'token': reset_token,
            'new_password': 'NewSecurePassword123!'
        }
        response = self.client.post(url_reset, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('Password reset successfully', response.data['message'])
        
        # Verify old password fails, new works
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewSecurePassword123!'))
        self.assertFalse(self.user.check_password('OldPassword123!'))

    def test_forgot_password_invalid_email(self):
        url = reverse('api:forgot-password')
        response = self.client.post(url, {'email': 'nonexistent@example.com'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('User with this email not found', response.data['email'][0])

