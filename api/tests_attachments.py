"""Tests for Sprint 2 — Item 1b: media attachments.

Attachments are sent inline as part of multipart create requests on:
- POST /api/questions/
- POST /api/questions/{id}/answers/
- POST /api/answers/{id}/replies/

The single new dedicated endpoint is DELETE /api/attachments/{id}/."""

import io

from django.test import TestCase
from django.urls import reverse
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.contenttypes.models import ContentType
from rest_framework import status
from rest_framework.test import APIClient

from .models import User, Specialization, Question, Answer, Attachment


def _make_user(email, username, phone):
    return User.objects.create_user(
        email=email,
        username=username,
        password='AttachPass123!',
        first_name='A',
        last_name='User',
        phone_number=phone,
    )


def _spec(name='Backend'):
    return Specialization.objects.get_or_create(name=name, defaults={'description': ''})[0]


def _file(name, content_type, size_bytes=1024):
    """Build a SimpleUploadedFile of the given size and MIME type."""
    return SimpleUploadedFile(name, b'x' * size_bytes, content_type=content_type)


class AttachmentImageTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = _make_user('img@example.com', 'imguser01', '+1100000001')
        self.spec = _spec('Backend')
        self.client.force_authenticate(user=self.user)

    def tearDown(self):
        cache.clear()

    def _create_question_with(self, attachments):
        return self.client.post(
            reverse('api:questions'),
            {
                'content': 'Question with attachments',
                'specializations': [str(self.spec.id)],
                'attachments': attachments,
            },
            format='multipart',
        )

    def test_create_question_with_jpeg(self):
        f = _file('photo.jpg', 'image/jpeg', size_bytes=1024)
        res = self._create_question_with([f])
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertEqual(len(res.data['attachments']), 1)
        self.assertEqual(res.data['attachments'][0]['kind'], 'image')

    def test_create_question_with_png(self):
        res = self._create_question_with([_file('photo.png', 'image/png')])
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertEqual(res.data['attachments'][0]['kind'], 'image')

    def test_create_question_with_webp(self):
        res = self._create_question_with([_file('photo.webp', 'image/webp')])
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_image_too_large_400(self):
        f = _file('huge.jpg', 'image/jpeg', size_bytes=6 * 1024 * 1024)  # 6 MB
        res = self._create_question_with([f])
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class AttachmentVideoTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = _make_user('vid@example.com', 'videouser1', '+1100000002')
        self.spec = _spec('Backend')
        self.client.force_authenticate(user=self.user)

    def tearDown(self):
        cache.clear()

    def _create_question_with(self, attachments):
        return self.client.post(
            reverse('api:questions'),
            {
                'content': 'Q with video',
                'specializations': [str(self.spec.id)],
                'attachments': attachments,
            },
            format='multipart',
        )

    def test_create_question_with_mp4(self):
        res = self._create_question_with([_file('clip.mp4', 'video/mp4', size_bytes=1024)])
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertEqual(res.data['attachments'][0]['kind'], 'video')

    def test_create_question_with_quicktime(self):
        res = self._create_question_with([_file('clip.mov', 'video/quicktime')])
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_video_too_large_400(self):
        f = _file('big.mp4', 'video/mp4', size_bytes=51 * 1024 * 1024)  # 51 MB
        res = self._create_question_with([f])
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class AttachmentAudioTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = _make_user('aud@example.com', 'audiouser1', '+1100000003')
        self.spec = _spec('Backend')
        self.client.force_authenticate(user=self.user)

    def tearDown(self):
        cache.clear()

    def _create_question_with(self, attachments):
        return self.client.post(
            reverse('api:questions'),
            {
                'content': 'Q with audio',
                'specializations': [str(self.spec.id)],
                'attachments': attachments,
            },
            format='multipart',
        )

    def test_create_question_with_mp3(self):
        res = self._create_question_with([_file('voice.mp3', 'audio/mpeg', size_bytes=1024)])
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertEqual(res.data['attachments'][0]['kind'], 'audio')

    def test_create_question_with_m4a(self):
        res = self._create_question_with([_file('voice.m4a', 'audio/mp4')])
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_audio_too_large_400(self):
        f = _file('big.mp3', 'audio/mpeg', size_bytes=16 * 1024 * 1024)  # 16 MB
        res = self._create_question_with([f])
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class AttachmentPdfTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = _make_user('pdf@example.com', 'pdfuser01', '+1100000004')
        self.spec = _spec('Backend')
        self.client.force_authenticate(user=self.user)

    def tearDown(self):
        cache.clear()

    def _create_question_with(self, attachments):
        return self.client.post(
            reverse('api:questions'),
            {
                'content': 'Q with pdf',
                'specializations': [str(self.spec.id)],
                'attachments': attachments,
            },
            format='multipart',
        )

    def test_create_question_with_valid_pdf(self):
        res = self._create_question_with([_file('doc.pdf', 'application/pdf', size_bytes=1024)])
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertEqual(res.data['attachments'][0]['kind'], 'pdf')

    def test_pdf_too_large_400(self):
        f = _file('big.pdf', 'application/pdf', size_bytes=11 * 1024 * 1024)  # 11 MB
        res = self._create_question_with([f])
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class AttachmentValidationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = _make_user('val@example.com', 'valuser01', '+1100000005')
        self.spec = _spec('Backend')
        self.client.force_authenticate(user=self.user)

    def tearDown(self):
        cache.clear()

    def _create_question_with(self, attachments):
        return self.client.post(
            reverse('api:questions'),
            {
                'content': 'Q for validation',
                'specializations': [str(self.spec.id)],
                'attachments': attachments,
            },
            format='multipart',
        )

    def test_unsupported_file_type_400(self):
        # .exe with executable MIME → unsupported
        f = _file('virus.exe', 'application/x-msdownload', size_bytes=1024)
        res = self._create_question_with([f])
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_attachments_above_per_request_cap_rejected(self):
        # 5 files in one request → ListField max_length=4 should reject
        files = [_file(f'a{i}.jpg', 'image/jpeg') for i in range(5)]
        res = self._create_question_with(files)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_one_bad_file_in_a_batch_rejects_whole_request(self):
        # First file valid, second invalid → entire request fails, no rows persisted
        files = [
            _file('ok.jpg', 'image/jpeg', size_bytes=1024),
            _file('bad.exe', 'application/x-msdownload', size_bytes=1024),
        ]
        res = self._create_question_with(files)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        # No question and no attachments should have been created.
        self.assertEqual(Attachment.objects.count(), 0)
        self.assertEqual(Question.objects.filter(author=self.user).count(), 0)

    def test_multipart_request_without_attachments_field_succeeds(self):
        res = self.client.post(
            reverse('api:questions'),
            {'content': 'multipart no files', 'specializations': [str(self.spec.id)]},
            format='multipart',
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertEqual(res.data['attachments'], [])

    def test_plain_json_request_still_works_no_attachments(self):
        # Backwards compat: existing JSON requests with no files keep working.
        res = self.client.post(
            reverse('api:questions'),
            {'content': 'no files', 'specializations': [str(self.spec.id)]},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['attachments'], [])

    def test_anonymous_attempt_to_attach_returns_401(self):
        self.client.force_authenticate(user=None)
        res = self._create_question_with([_file('x.jpg', 'image/jpeg')])
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AttachmentDeleteTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.author = _make_user('a1@example.com', 'a1user001', '+1100000006')
        self.other = _make_user('a2@example.com', 'a2user001', '+1100000007')
        self.spec = _spec('Backend')

        # Author creates a question with one image attachment
        self.client.force_authenticate(user=self.author)
        res = self.client.post(
            reverse('api:questions'),
            {
                'content': 'Q for delete tests',
                'specializations': [str(self.spec.id)],
                'attachments': [_file('one.jpg', 'image/jpeg', size_bytes=1024)],
            },
            format='multipart',
        )
        self.q_id = res.data['id']
        self.attachment_id = res.data['attachments'][0]['id']

    def tearDown(self):
        cache.clear()

    def test_author_can_delete_own_attachment(self):
        res = self.client.delete(reverse('api:attachment-delete', args=[self.attachment_id]))
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Attachment.objects.filter(id=self.attachment_id).exists())

    def test_non_author_cannot_delete(self):
        self.client.force_authenticate(user=self.other)
        res = self.client.delete(reverse('api:attachment-delete', args=[self.attachment_id]))
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Attachment.objects.filter(id=self.attachment_id).exists())

    def test_anonymous_cannot_delete(self):
        self.client.force_authenticate(user=None)
        res = self.client.delete(reverse('api:attachment-delete', args=[self.attachment_id]))
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_nonexistent_attachment_404(self):
        import uuid
        res = self.client.delete(reverse('api:attachment-delete', args=[uuid.uuid4()]))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_cascade_deletion_when_parent_question_deleted(self):
        # Deleting the question via the question-detail endpoint should cascade
        # to the Attachment row (handled by the GenericRelation reverse FK).
        res = self.client.delete(reverse('api:question-detail', args=[self.q_id]))
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Attachment.objects.filter(id=self.attachment_id).exists())


class AttachmentReadIntegrationTests(TestCase):
    """Verify attachments are exposed correctly in question/answer/reply read responses."""

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = _make_user('read@example.com', 'readuser1', '+1100000008')
        self.spec = _spec('Backend')
        self.client.force_authenticate(user=self.user)

    def tearDown(self):
        cache.clear()

    def test_question_detail_returns_attachments(self):
        res = self.client.post(
            reverse('api:questions'),
            {
                'content': 'with files',
                'specializations': [str(self.spec.id)],
                'attachments': [
                    _file('a.jpg', 'image/jpeg'),
                    _file('b.pdf', 'application/pdf'),
                ],
            },
            format='multipart',
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        q_id = res.data['id']

        detail = self.client.get(reverse('api:question-detail', args=[q_id]))
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertEqual(len(detail.data['attachments']), 2)
        kinds = {a['kind'] for a in detail.data['attachments']}
        self.assertEqual(kinds, {'image', 'pdf'})

    def test_answer_create_with_attachment(self):
        # Create a question first (no attachments)
        q = self.client.post(
            reverse('api:questions'),
            {'content': 'q', 'specializations': [str(self.spec.id)]},
            format='json',
        )
        # Post an answer with an audio file
        res = self.client.post(
            reverse('api:question-answers', args=[q.data['id']]),
            {
                'content': 'audio answer',
                'attachments': [_file('voice.mp3', 'audio/mpeg', size_bytes=1024)],
            },
            format='multipart',
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertEqual(len(res.data['attachments']), 1)
        self.assertEqual(res.data['attachments'][0]['kind'], 'audio')

    def test_reply_create_with_attachment(self):
        q = self.client.post(
            reverse('api:questions'),
            {'content': 'q', 'specializations': [str(self.spec.id)]},
            format='json',
        )
        a = self.client.post(
            reverse('api:question-answers', args=[q.data['id']]),
            {'content': 'a'},
            format='json',
        )
        res = self.client.post(
            reverse('api:answer-replies', args=[a.data['id']]),
            {
                'content': 'reply with image',
                'attachments': [_file('img.png', 'image/png')],
            },
            format='multipart',
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertEqual(len(res.data['attachments']), 1)
        self.assertEqual(res.data['attachments'][0]['kind'], 'image')
