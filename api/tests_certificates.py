"""Tests for Sprint 2 — Item 4: Certificate endpoints.

The Certificate model itself shipped in Sprint 1; this sprint adds the
endpoints that let users manage their own and view others' certificates."""

from datetime import date

from django.test import TestCase
from django.urls import reverse
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APIClient

from .models import User, Certificate


def _make_user(email, username, phone):
    return User.objects.create_user(
        email=email,
        username=username,
        password='CertPass123!',
        first_name='C',
        last_name='User',
        phone_number=phone,
    )


class CertificateTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.alice = _make_user('cert-a@example.com', 'certalice1', '+1500000001')
        self.bob = _make_user('cert-b@example.com', 'certbob01', '+1500000002')

    def tearDown(self):
        cache.clear()

    # --- Listing my own certificates ---

    def test_my_certificates_requires_auth(self):
        res = self.client.get(reverse('api:my-certificates'))
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_my_certificates_starts_empty(self):
        self.client.force_authenticate(user=self.alice)
        res = self.client.get(reverse('api:my-certificates'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Paginated → results is empty list
        self.assertEqual(res.data['count'], 0)

    def test_my_certificates_returns_only_mine(self):
        Certificate.objects.create(
            user=self.alice, title="Alice cert", issuer="Org",
            issue_date=date(2026, 1, 1),
            certificate_url="https://example.com/cert/a",
        )
        Certificate.objects.create(
            user=self.bob, title="Bob cert", issuer="Org",
            issue_date=date(2026, 1, 1),
            certificate_url="https://example.com/cert/b",
        )

        self.client.force_authenticate(user=self.alice)
        res = self.client.get(reverse('api:my-certificates'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['count'], 1)
        self.assertEqual(res.data['results'][0]['title'], "Alice cert")

    # --- Creating ---

    def test_create_certificate_requires_auth(self):
        res = self.client.post(
            reverse('api:my-certificates'),
            {
                'title': 'X',
                'issuer': 'Y',
                'issue_date': '2026-01-01',
                'certificate_url': 'https://example.com',
            },
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_certificate_success(self):
        self.client.force_authenticate(user=self.alice)
        res = self.client.post(
            reverse('api:my-certificates'),
            {
                'title': 'Django Mastery',
                'issuer': 'edX',
                'issue_date': '2026-04-15',
                'certificate_url': 'https://example.com/cert/abc',
            },
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        # Owner should be the request user, not whatever the client sends
        cert = Certificate.objects.get(id=res.data['id'])
        self.assertEqual(cert.user_id, self.alice.id)

    def test_create_certificate_with_bad_url_400(self):
        self.client.force_authenticate(user=self.alice)
        res = self.client.post(
            reverse('api:my-certificates'),
            {
                'title': 'X',
                'issuer': 'Y',
                'issue_date': '2026-01-01',
                'certificate_url': 'not-a-url',
            },
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('certificate_url', res.data)

    def test_create_certificate_user_field_in_body_is_ignored(self):
        # Even if Alice tries to spoof Bob as the owner, the server uses
        # request.user via perform_create.
        self.client.force_authenticate(user=self.alice)
        res = self.client.post(
            reverse('api:my-certificates'),
            {
                'title': 'Sneaky',
                'issuer': 'Y',
                'issue_date': '2026-01-01',
                'certificate_url': 'https://example.com',
                'user': str(self.bob.id),  # ← attempt at impersonation
            },
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        cert = Certificate.objects.get(id=res.data['id'])
        self.assertEqual(cert.user_id, self.alice.id)  # Alice, not Bob

    # --- Deleting ---

    def test_delete_my_certificate(self):
        cert = Certificate.objects.create(
            user=self.alice, title="X", issuer="Y",
            issue_date=date(2026, 1, 1),
            certificate_url="https://example.com",
        )
        self.client.force_authenticate(user=self.alice)
        res = self.client.delete(
            reverse('api:my-certificate-delete', args=[cert.id])
        )
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Certificate.objects.filter(id=cert.id).exists())

    def test_cannot_delete_someone_elses_certificate(self):
        # Bob's certificate
        cert = Certificate.objects.create(
            user=self.bob, title="X", issuer="Y",
            issue_date=date(2026, 1, 1),
            certificate_url="https://example.com",
        )
        self.client.force_authenticate(user=self.alice)
        res = self.client.delete(
            reverse('api:my-certificate-delete', args=[cert.id])
        )
        # Queryset filters by request.user → 404, not 403, by design
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Certificate.objects.filter(id=cert.id).exists())

    def test_delete_certificate_requires_auth(self):
        cert = Certificate.objects.create(
            user=self.alice, title="X", issuer="Y",
            issue_date=date(2026, 1, 1),
            certificate_url="https://example.com",
        )
        res = self.client.delete(
            reverse('api:my-certificate-delete', args=[cert.id])
        )
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    # --- Public view ---

    def test_public_user_certificates_anyone_can_read(self):
        Certificate.objects.create(
            user=self.alice, title="A", issuer="Y",
            issue_date=date(2026, 1, 1),
            certificate_url="https://example.com/a",
        )
        Certificate.objects.create(
            user=self.alice, title="B", issuer="Y",
            issue_date=date(2026, 6, 1),
            certificate_url="https://example.com/b",
        )

        # Anonymous reader
        self.client.force_authenticate(user=None)
        res = self.client.get(
            reverse('api:user-certificates', args=[self.alice.id])
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['count'], 2)
        # Newest issue date first
        self.assertEqual(res.data['results'][0]['title'], "B")

    def test_public_user_certificates_empty_for_user_with_none(self):
        self.client.force_authenticate(user=None)
        res = self.client.get(
            reverse('api:user-certificates', args=[self.bob.id])
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['count'], 0)
