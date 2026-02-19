from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from .models import User, Specialization, UserSpecialization


class SpecializationFlowTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='TestPassword123!',
            first_name='Test',
            last_name='User'
        )

        self.spec1 = Specialization.objects.create(
            name='Backend Development',
            description='Server-side development'
        )
        self.spec2 = Specialization.objects.create(
            name='Frontend Development',
            description='Client-side development'
        )
        self.spec3 = Specialization.objects.create(
            name='Machine Learning',
            description='AI and ML'
        )

    def test_get_specializations_list(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('api:specializations')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('count', response.data)
        self.assertIn('results', response.data)
        self.assertEqual(response.data['count'], 3)

    def test_get_specializations_empty_list(self):
        Specialization.objects.all().delete()

        self.client.force_authenticate(user=self.user)
        url = reverse('api:specializations')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertEqual(response.data['results'], [])

    def test_get_user_specializations_initial(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('api:user-specializations')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data['specialization_form_completed_at'])
        self.assertEqual(response.data['specializations'], [])

    def test_set_user_specializations(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('api:user-specializations')

        data = {
            'specialization_ids': [str(self.spec1.id), str(self.spec2.id)]
        }
        response = self.client.put(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data['specialization_form_completed_at'])
        self.assertEqual(len(response.data['specializations']), 2)

        self.assertEqual(self.user.specializations.count(), 2)

    def test_replace_user_specializations(self):
        UserSpecialization.objects.create(user=self.user, specialization=self.spec1)

        self.client.force_authenticate(user=self.user)
        url = reverse('api:user-specializations')

        data = {
            'specialization_ids': [str(self.spec2.id), str(self.spec3.id)]
        }
        response = self.client.put(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['specializations']), 2)

        spec_ids = [s['id'] for s in response.data['specializations']]
        self.assertNotIn(str(self.spec1.id), spec_ids)

    def test_skip_specialization_form(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('api:user-specializations')

        data = {'skip': True}
        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data['specialization_form_completed_at'])
        self.assertEqual(response.data['specializations'], [])

        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.specialization_form_completed_at)

    def test_skip_then_add_specializations(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('api:user-specializations')

        self.client.patch(url, {'skip': True}, format='json')

        data = {
            'specialization_ids': [str(self.spec1.id)]
        }
        response = self.client.put(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['specializations']), 1)

    def test_invalid_specialization_id(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('api:user-specializations')

        import uuid
        invalid_id = str(uuid.uuid4())

        data = {
            'specialization_ids': [invalid_id]
        }
        response = self.client.put(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('specialization_ids', response.data)

    def test_duplicate_prevention(self):
        UserSpecialization.objects.create(user=self.user, specialization=self.spec1)

        with self.assertRaises(Exception):
            UserSpecialization.objects.create(user=self.user, specialization=self.spec1)

        self.assertEqual(self.user.specializations.count(), 1)

    def test_empty_specialization_list(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('api:user-specializations')

        data = {
            'specialization_ids': []
        }
        response = self.client.put(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data['specialization_form_completed_at'])
        self.assertEqual(response.data['specializations'], [])

    def test_unauthenticated_access_denied(self):
        url = reverse('api:specializations')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        url = reverse('api:user-specializations')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
