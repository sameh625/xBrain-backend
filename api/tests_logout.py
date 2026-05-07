"""Tests for Sprint 2 — Item 5: Logout endpoint.

POST /api/auth/logout/ blacklists a refresh token so it can no longer
be exchanged for a new access token. Access tokens expire naturally."""

from django.test import TestCase
from django.urls import reverse
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User


def _make_user():
    return User.objects.create_user(
        email='logout@example.com',
        username='logoutuser',
        password='LogoutPass123!',
        first_name='L',
        last_name='User',
        phone_number='+1300000001',
    )


class LogoutTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = _make_user()
        self.refresh = RefreshToken.for_user(self.user)
        self.access_token = str(self.refresh.access_token)
        self.refresh_token = str(self.refresh)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

    def tearDown(self):
        cache.clear()

    def test_logout_requires_auth(self):
        # No Authorization header → 401
        self.client.credentials()
        res = self.client.post(
            reverse('api:logout'),
            {'refresh': self.refresh_token},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_with_missing_refresh_returns_400(self):
        res = self.client.post(reverse('api:logout'), {}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('refresh', res.data)

    def test_logout_with_invalid_refresh_returns_400(self):
        res = self.client.post(
            reverse('api:logout'),
            {'refresh': 'not-a-real-token'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('refresh', res.data)

    def test_logout_blacklists_refresh_token(self):
        res = self.client.post(
            reverse('api:logout'),
            {'refresh': self.refresh_token},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_205_RESET_CONTENT)

        # Try to use the same refresh token afterwards → 401 from token-refresh
        # because it's blacklisted.
        self.client.credentials()  # no auth needed for token refresh
        retry = self.client.post(
            reverse('api:token-refresh'),
            {'refresh': self.refresh_token},
            format='json',
        )
        self.assertEqual(retry.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_twice_with_same_token_second_returns_400(self):
        # First logout works
        first = self.client.post(
            reverse('api:logout'),
            {'refresh': self.refresh_token},
            format='json',
        )
        self.assertEqual(first.status_code, status.HTTP_205_RESET_CONTENT)

        # Second logout with the same (now blacklisted) token → 400
        second = self.client.post(
            reverse('api:logout'),
            {'refresh': self.refresh_token},
            format='json',
        )
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
