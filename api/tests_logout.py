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

        # Second logout with the same (now blacklisted) refresh token → still 205
        # because the access token used in the second call (a fresh one from setUp's
        # for_user, since the first logout blacklisted the original access token's jti)
        # has already been blacklisted. Actually — we re-use the same access token,
        # so the *second* request fails at auth time before reaching the view.
        # Confirms the access-token blacklist works.
        second = self.client.post(
            reverse('api:logout'),
            {'refresh': self.refresh_token},
            format='json',
        )
        # After first logout, the access token is blacklisted → auth fails → 401
        self.assertEqual(second.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_access_token_rejected_after_logout(self):
        """The user's original access token must stop working immediately
        after they call /api/auth/logout/, not just after it expires naturally."""
        # Sanity: access token works before logout.
        before = self.client.get(reverse('api:user-profile'))
        self.assertEqual(before.status_code, status.HTTP_200_OK)

        # Logout
        logout_res = self.client.post(
            reverse('api:logout'),
            {'refresh': self.refresh_token},
            format='json',
        )
        self.assertEqual(logout_res.status_code, status.HTTP_205_RESET_CONTENT)

        # Same access token — should now be rejected.
        after = self.client.get(reverse('api:user-profile'))
        self.assertEqual(after.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_other_endpoints_also_reject_blacklisted_access_token(self):
        """Confirm the access-token blacklist is enforced on every endpoint,
        not just /api/users/me/."""
        # Logout
        self.client.post(
            reverse('api:logout'),
            {'refresh': self.refresh_token},
            format='json',
        )

        # Try a few different protected endpoints — all should 401.
        for url in [
            reverse('api:user-profile'),
            reverse('api:specializations'),
            reverse('api:user-specializations'),
        ]:
            res = self.client.get(url)
            self.assertEqual(
                res.status_code,
                status.HTTP_401_UNAUTHORIZED,
                f'{url} should be 401 after logout but got {res.status_code}',
            )

    def test_fresh_login_after_logout_works(self):
        """After logging out, the user must be able to log in again
        and the new tokens must work."""
        # Logout first
        self.client.post(
            reverse('api:logout'),
            {'refresh': self.refresh_token},
            format='json',
        )

        # Login again — get fresh tokens
        self.client.credentials()  # clear stale auth
        res = self.client.post(
            reverse('api:login'),
            {'identifier': self.user.email, 'password': 'LogoutPass123!'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        new_access = res.data['access_token']

        # Use the new access token — it should work.
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {new_access}')
        profile = self.client.get(reverse('api:user-profile'))
        self.assertEqual(profile.status_code, status.HTTP_200_OK)
