"""Tests for Sprint 2 — Item 1: Questions & Answers.

Decisions baked in:
- D1 = yes: a user *can* answer their own question.
- D2 = anyone authenticated can reply to any answer.
- D3 = question detail embeds first 10 top-level answers, each with first 2 replies inline.
"""

from django.test import TestCase
from django.urls import reverse
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APIClient

from .models import User, Specialization, Question, Answer


def _make_user(email, username, phone):
    return User.objects.create_user(
        email=email,
        username=username,
        password='TestPass123!',
        first_name='T',
        last_name='User',
        phone_number=phone,
    )


def _spec(name):
    return Specialization.objects.create(name=name, description='')


class QuestionTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.asker = _make_user('asker@example.com', 'askeruser', '+1000000001')
        self.other = _make_user('other@example.com', 'otheruser', '+1000000002')
        self.s_backend = _spec('Backend')
        self.s_ml = _spec('ML')
        self.s_frontend = _spec('Frontend')
        self.s_devops = _spec('DevOps')

    def tearDown(self):
        cache.clear()

    def _create_question(self, author=None, content='How do I deploy?', spec_ids=None):
        author = author or self.asker
        spec_ids = spec_ids if spec_ids is not None else [str(self.s_backend.id)]
        self.client.force_authenticate(user=author)
        return self.client.post(
            reverse('api:questions'),
            {'content': content, 'specializations': spec_ids},
            format='json',
        )

    # --- Create ---

    def test_create_requires_auth(self):
        self.client.force_authenticate(user=None)
        res = self.client.post(
            reverse('api:questions'),
            {'content': 'Hi', 'specializations': [str(self.s_backend.id)]},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_with_one_specialization(self):
        res = self._create_question(spec_ids=[str(self.s_backend.id)])
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertEqual(len(res.data['specializations']), 1)

    def test_create_with_multiple_specializations(self):
        res = self._create_question(
            spec_ids=[str(self.s_backend.id), str(self.s_ml.id), str(self.s_frontend.id)]
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertEqual(len(res.data['specializations']), 3)

    def test_create_with_more_than_three_specializations_400(self):
        res = self._create_question(
            spec_ids=[str(self.s_backend.id), str(self.s_ml.id), str(self.s_frontend.id), str(self.s_devops.id)]
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('specializations', res.data)

    def test_create_with_zero_specializations_400(self):
        res = self._create_question(spec_ids=[])
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('specializations', res.data)

    def test_create_with_specializations_field_omitted_400(self):
        self.client.force_authenticate(user=self.asker)
        res = self.client.post(
            reverse('api:questions'),
            {'content': 'X'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('specializations', res.data)

    def test_create_content_too_long_400(self):
        long_content = 'a' * 5001
        res = self._create_question(content=long_content)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('content', res.data)

    def test_create_content_empty_400(self):
        res = self._create_question(content='   ')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('content', res.data)

    # --- List ---

    def test_list_paginated_newest_first(self):
        self._create_question(content='oldest')
        self._create_question(content='middle')
        self._create_question(content='newest')
        self.client.force_authenticate(user=self.other)
        res = self.client.get(reverse('api:questions'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        results = res.data['results']
        self.assertEqual(len(results), 3)
        self.assertTrue(results[0]['content_preview'].startswith('newest'))
        self.assertTrue(results[2]['content_preview'].startswith('oldest'))

    def test_filter_by_author(self):
        self._create_question(author=self.asker, content='asker q')
        self._create_question(author=self.other, content='other q')
        self.client.force_authenticate(user=self.asker)
        res = self.client.get(reverse('api:questions'), {'author': str(self.asker.id)})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data['results']), 1)
        self.assertTrue(res.data['results'][0]['content_preview'].startswith('asker q'))

    def test_filter_by_specialization_returns_questions_with_that_spec_even_among_others(self):
        # Q1: backend + ml
        self._create_question(spec_ids=[str(self.s_backend.id), str(self.s_ml.id)])
        # Q2: backend only
        self._create_question(spec_ids=[str(self.s_backend.id)])
        # Q3: frontend only
        self._create_question(spec_ids=[str(self.s_frontend.id)])

        self.client.force_authenticate(user=self.asker)
        res = self.client.get(reverse('api:questions'), {'specialization': str(self.s_backend.id)})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # 2 questions are tagged with Backend
        self.assertEqual(len(res.data['results']), 2)

    def test_filter_by_is_resolved_true(self):
        r1 = self._create_question(content='unresolved')
        r2 = self._create_question(content='resolved')
        # Resolve r2
        q2_id = r2.data['id']
        self.client.force_authenticate(user=self.asker)
        self.client.post(reverse('api:question-resolve', args=[q2_id]))

        res = self.client.get(reverse('api:questions'), {'is_resolved': 'true'})
        self.assertEqual(len(res.data['results']), 1)
        self.assertTrue(res.data['results'][0]['is_resolved'])

    def test_search_by_q(self):
        self._create_question(content='How do I deploy Django on Azure')
        self._create_question(content='Best ML libraries in Python')
        self.client.force_authenticate(user=self.asker)
        res = self.client.get(reverse('api:questions'), {'q': 'Azure'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data['results']), 1)

    # --- Detail ---

    def test_detail_includes_inline_answers_and_replies(self):
        r = self._create_question(content='Question with thread')
        q_id = r.data['id']

        # 2 top-level answers, second one has 3 replies
        self.client.force_authenticate(user=self.other)
        a1_url = reverse('api:question-answers', args=[q_id])
        a1 = self.client.post(a1_url, {'content': 'first answer'}, format='json')
        a2 = self.client.post(a1_url, {'content': 'second answer'}, format='json')
        a2_id = a2.data['id']

        rep_url = reverse('api:answer-replies', args=[a2_id])
        for i in range(3):
            self.client.post(rep_url, {'content': f'reply {i}'}, format='json')

        # Now get question detail
        self.client.force_authenticate(user=self.asker)
        res = self.client.get(reverse('api:question-detail', args=[q_id]))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # answers_count is the Facebook-style total: 2 top-level + 3 replies = 5
        self.assertEqual(res.data['answers_count'], 5)
        self.assertNotIn('replies_count', res.data)  # field is gone from question payload
        self.assertEqual(len(res.data['answers']), 2)
        # First inline answer has no replies, second has first 2 replies inline
        a2_in_detail = [a for a in res.data['answers'] if a['id'] == a2_id][0]
        self.assertEqual(a2_in_detail['replies_count'], 3)
        self.assertEqual(len(a2_in_detail['replies']), 2)

    # --- Update ---

    def test_patch_question_author_only(self):
        r = self._create_question(content='original')
        q_id = r.data['id']

        # Author can patch
        self.client.force_authenticate(user=self.asker)
        res = self.client.patch(
            reverse('api:question-detail', args=[q_id]),
            {'content': 'edited', 'specializations': [str(self.s_ml.id)]},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.assertEqual(res.data['content'], 'edited')

        # Non-author cannot
        self.client.force_authenticate(user=self.other)
        res = self.client.patch(
            reverse('api:question-detail', args=[q_id]),
            {'content': 'hacked', 'specializations': [str(self.s_ml.id)]},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    # --- Delete ---

    def test_delete_question_cascades_to_answers_and_replies(self):
        r = self._create_question()
        q_id = r.data['id']

        self.client.force_authenticate(user=self.other)
        a = self.client.post(
            reverse('api:question-answers', args=[q_id]),
            {'content': 'an answer'},
            format='json',
        )
        a_id = a.data['id']
        self.client.post(
            reverse('api:answer-replies', args=[a_id]),
            {'content': 'a reply'},
            format='json',
        )

        self.assertEqual(Answer.objects.filter(question_id=q_id).count(), 2)

        self.client.force_authenticate(user=self.asker)
        res = self.client.delete(reverse('api:question-detail', args=[q_id]))
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

        self.assertFalse(Question.objects.filter(id=q_id).exists())
        self.assertEqual(Answer.objects.filter(question_id=q_id).count(), 0)


class ResolveUnresolveTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.asker = _make_user('asker2@example.com', 'asker2us', '+1000000003')
        self.other = _make_user('other2@example.com', 'other2us', '+1000000004')
        self.spec = _spec('Backend')
        self.client.force_authenticate(user=self.asker)
        r = self.client.post(
            reverse('api:questions'),
            {'content': 'Q', 'specializations': [str(self.spec.id)]},
            format='json',
        )
        self.q_id = r.data['id']

    def tearDown(self):
        cache.clear()

    def test_resolve_as_asker(self):
        res = self.client.post(reverse('api:question-resolve', args=[self.q_id]))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data['is_resolved'])
        self.assertIsNotNone(res.data['resolved_at'])

    def test_resolve_already_resolved_is_noop(self):
        self.client.post(reverse('api:question-resolve', args=[self.q_id]))
        res = self.client.post(reverse('api:question-resolve', args=[self.q_id]))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data['is_resolved'])

    def test_resolve_as_non_asker_403(self):
        self.client.force_authenticate(user=self.other)
        res = self.client.post(reverse('api:question-resolve', args=[self.q_id]))
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_unresolve_as_asker(self):
        self.client.post(reverse('api:question-resolve', args=[self.q_id]))
        res = self.client.post(reverse('api:question-unresolve', args=[self.q_id]))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertFalse(res.data['is_resolved'])
        self.assertIsNone(res.data['resolved_at'])

    def test_unresolve_already_unresolved_is_noop(self):
        res = self.client.post(reverse('api:question-unresolve', args=[self.q_id]))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertFalse(res.data['is_resolved'])

    def test_unresolve_as_non_asker_403(self):
        self.client.post(reverse('api:question-resolve', args=[self.q_id]))
        self.client.force_authenticate(user=self.other)
        res = self.client.post(reverse('api:question-unresolve', args=[self.q_id]))
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AnswerTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.asker = _make_user('asker3@example.com', 'asker3us', '+1000000005')
        self.answerer = _make_user('answer@example.com', 'answeruser', '+1000000006')
        self.spec = _spec('Backend')
        self.client.force_authenticate(user=self.asker)
        r = self.client.post(
            reverse('api:questions'),
            {'content': 'Q', 'specializations': [str(self.spec.id)]},
            format='json',
        )
        self.q_id = r.data['id']

    def tearDown(self):
        cache.clear()

    def test_post_answer_requires_auth(self):
        self.client.force_authenticate(user=None)
        res = self.client.post(
            reverse('api:question-answers', args=[self.q_id]),
            {'content': 'a'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_top_level_answers(self):
        self.client.force_authenticate(user=self.answerer)
        self.client.post(reverse('api:question-answers', args=[self.q_id]), {'content': 'A1'}, format='json')
        a2 = self.client.post(reverse('api:question-answers', args=[self.q_id]), {'content': 'A2'}, format='json')
        # Add a reply to A2 — should NOT show up in top-level list
        self.client.post(reverse('api:answer-replies', args=[a2.data['id']]), {'content': 'reply'}, format='json')

        res = self.client.get(reverse('api:question-answers', args=[self.q_id]))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data['results']), 2)

    def test_self_answer_allowed(self):
        # D1 = yes
        self.client.force_authenticate(user=self.asker)
        res = self.client.post(
            reverse('api:question-answers', args=[self.q_id]),
            {'content': 'I figured it out myself'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)

    def test_patch_answer_author_only(self):
        self.client.force_authenticate(user=self.answerer)
        a = self.client.post(reverse('api:question-answers', args=[self.q_id]), {'content': 'orig'}, format='json')
        a_id = a.data['id']

        # Author can patch
        res = self.client.patch(reverse('api:answer-detail', args=[a_id]), {'content': 'edited'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['content'], 'edited')

        # Non-author cannot
        self.client.force_authenticate(user=self.asker)
        res = self.client.patch(reverse('api:answer-detail', args=[a_id]), {'content': 'hacked'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_answer_cascades_to_replies(self):
        self.client.force_authenticate(user=self.answerer)
        a = self.client.post(reverse('api:question-answers', args=[self.q_id]), {'content': 'A'}, format='json')
        a_id = a.data['id']
        self.client.post(reverse('api:answer-replies', args=[a_id]), {'content': 'r1'}, format='json')
        self.client.post(reverse('api:answer-replies', args=[a_id]), {'content': 'r2'}, format='json')

        self.assertEqual(Answer.objects.filter(parent_answer_id=a_id).count(), 2)

        res = self.client.delete(reverse('api:answer-detail', args=[a_id]))
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Answer.objects.filter(id=a_id).exists())
        self.assertEqual(Answer.objects.filter(parent_answer_id=a_id).count(), 0)

    def test_post_answer_to_nonexistent_question_404(self):
        self.client.force_authenticate(user=self.answerer)
        import uuid
        fake = uuid.uuid4()
        res = self.client.post(
            reverse('api:question-answers', args=[fake]),
            {'content': 'a'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_post_answer_with_empty_content_400(self):
        self.client.force_authenticate(user=self.answerer)
        res = self.client.post(
            reverse('api:question-answers', args=[self.q_id]),
            {'content': '   '},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class ReplyTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.asker = _make_user('asker4@example.com', 'asker4us', '+1000000007')
        self.answerer = _make_user('ans4@example.com', 'ans4user', '+1000000008')
        self.replier = _make_user('rep4@example.com', 'rep4user', '+1000000009')
        self.spec = _spec('Backend')

        # Create question
        self.client.force_authenticate(user=self.asker)
        q = self.client.post(
            reverse('api:questions'),
            {'content': 'Q', 'specializations': [str(self.spec.id)]},
            format='json',
        )
        self.q_id = q.data['id']

        # Create top-level answer
        self.client.force_authenticate(user=self.answerer)
        a = self.client.post(
            reverse('api:question-answers', args=[self.q_id]),
            {'content': 'top-level answer'},
            format='json',
        )
        self.a_id = a.data['id']

    def tearDown(self):
        cache.clear()

    def test_post_reply_requires_auth(self):
        self.client.force_authenticate(user=None)
        res = self.client.post(
            reverse('api:answer-replies', args=[self.a_id]),
            {'content': 'r'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_post_reply_by_asker(self):
        self.client.force_authenticate(user=self.asker)
        res = self.client.post(
            reverse('api:answer-replies', args=[self.a_id]),
            {'content': 'asker replies'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertEqual(str(res.data['parent_answer']), str(self.a_id))
        self.assertEqual(str(res.data['question']), str(self.q_id))

    def test_post_reply_by_random_user_allowed(self):
        # D2 = anyone authenticated
        self.client.force_authenticate(user=self.replier)
        res = self.client.post(
            reverse('api:answer-replies', args=[self.a_id]),
            {'content': 'random reply'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)

    def test_post_reply_to_a_reply_400(self):
        # First, a valid reply
        self.client.force_authenticate(user=self.replier)
        r1 = self.client.post(
            reverse('api:answer-replies', args=[self.a_id]),
            {'content': 'first reply'},
            format='json',
        )
        r1_id = r1.data['id']

        # Now try to reply to that reply — depth-1 should reject
        res = self.client.post(
            reverse('api:answer-replies', args=[r1_id]),
            {'content': 'reply to a reply'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('parent_answer', res.data)

    def test_list_replies_under_an_answer(self):
        self.client.force_authenticate(user=self.replier)
        for i in range(3):
            self.client.post(
                reverse('api:answer-replies', args=[self.a_id]),
                {'content': f'r{i}'},
                format='json',
            )

        res = self.client.get(reverse('api:answer-replies', args=[self.a_id]))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data['results']), 3)


# =====================================================================
# Edge cases: 404s, anonymous reads, auth requirements on writes,
# filter combinations, security, count consistency.
# =====================================================================


class NotFoundTests(TestCase):
    """All endpoints with a {id} URL kwarg should 404 cleanly when the row doesn't exist."""

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = _make_user('nf@example.com', 'nfuser01', '+1000001001')
        self.client.force_authenticate(user=self.user)
        import uuid
        self.fake = uuid.uuid4()

    def tearDown(self):
        cache.clear()

    def test_get_nonexistent_question_404(self):
        res = self.client.get(reverse('api:question-detail', args=[self.fake]))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_nonexistent_question_404(self):
        res = self.client.patch(
            reverse('api:question-detail', args=[self.fake]),
            {'content': 'x'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_nonexistent_question_404(self):
        res = self.client.delete(reverse('api:question-detail', args=[self.fake]))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_resolve_nonexistent_question_404(self):
        res = self.client.post(reverse('api:question-resolve', args=[self.fake]))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_unresolve_nonexistent_question_404(self):
        res = self.client.post(reverse('api:question-unresolve', args=[self.fake]))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_nonexistent_answer_404(self):
        res = self.client.get(reverse('api:answer-detail', args=[self.fake]))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_nonexistent_answer_404(self):
        res = self.client.patch(
            reverse('api:answer-detail', args=[self.fake]),
            {'content': 'x'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_nonexistent_answer_404(self):
        res = self.client.delete(reverse('api:answer-detail', args=[self.fake]))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_answers_under_nonexistent_question_404(self):
        res = self.client.get(reverse('api:question-answers', args=[self.fake]))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_replies_under_nonexistent_answer_404(self):
        res = self.client.get(reverse('api:answer-replies', args=[self.fake]))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_post_reply_to_nonexistent_answer_404(self):
        res = self.client.post(
            reverse('api:answer-replies', args=[self.fake]),
            {'content': 'r'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)


class AnonymousReadTests(TestCase):
    """Read endpoints work for unauthenticated users (IsAuthenticatedOrReadOnly)."""

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.author = _make_user('anon-author@example.com', 'anonauth1', '+1000002001')
        self.spec = _spec('Backend')

        self.client.force_authenticate(user=self.author)
        r = self.client.post(
            reverse('api:questions'),
            {'content': 'public question', 'specializations': [str(self.spec.id)]},
            format='json',
        )
        self.q_id = r.data['id']

        a = self.client.post(
            reverse('api:question-answers', args=[self.q_id]),
            {'content': 'public answer'},
            format='json',
        )
        self.a_id = a.data['id']

        self.client.post(
            reverse('api:answer-replies', args=[self.a_id]),
            {'content': 'public reply'},
            format='json',
        )

        # De-authenticate for the rest of the tests
        self.client.force_authenticate(user=None)

    def tearDown(self):
        cache.clear()

    def test_anonymous_can_list_questions(self):
        res = self.client.get(reverse('api:questions'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data['results']), 1)

    def test_anonymous_can_get_question_detail(self):
        res = self.client.get(reverse('api:question-detail', args=[self.q_id]))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['content'], 'public question')

    def test_anonymous_can_list_answers(self):
        res = self.client.get(reverse('api:question-answers', args=[self.q_id]))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data['results']), 1)

    def test_anonymous_can_list_replies(self):
        res = self.client.get(reverse('api:answer-replies', args=[self.a_id]))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data['results']), 1)

    def test_anonymous_cannot_create_question(self):
        res = self.client.post(
            reverse('api:questions'),
            {'content': 'x', 'specializations': [str(self.spec.id)]},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_anonymous_cannot_resolve_question(self):
        res = self.client.post(reverse('api:question-resolve', args=[self.q_id]))
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class WriteAuthTests(TestCase):
    """All mutating endpoints require auth (return 401 when called without a token)."""

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        author = _make_user('writeauth@example.com', 'writeauth1', '+1000003001')
        spec = _spec('Backend')

        self.client.force_authenticate(user=author)
        r = self.client.post(
            reverse('api:questions'),
            {'content': 'q', 'specializations': [str(spec.id)]},
            format='json',
        )
        self.q_id = r.data['id']

        a = self.client.post(
            reverse('api:question-answers', args=[self.q_id]),
            {'content': 'a'},
            format='json',
        )
        self.a_id = a.data['id']

        self.client.force_authenticate(user=None)

    def tearDown(self):
        cache.clear()

    def test_patch_question_requires_auth(self):
        res = self.client.patch(
            reverse('api:question-detail', args=[self.q_id]),
            {'content': 'x'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_question_requires_auth(self):
        res = self.client.delete(reverse('api:question-detail', args=[self.q_id]))
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_resolve_requires_auth(self):
        res = self.client.post(reverse('api:question-resolve', args=[self.q_id]))
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unresolve_requires_auth(self):
        res = self.client.post(reverse('api:question-unresolve', args=[self.q_id]))
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_patch_answer_requires_auth(self):
        res = self.client.patch(
            reverse('api:answer-detail', args=[self.a_id]),
            {'content': 'x'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_answer_requires_auth(self):
        res = self.client.delete(reverse('api:answer-detail', args=[self.a_id]))
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PatchValidationTests(TestCase):
    """PATCH on Question should enforce the same spec count + content rules as POST."""

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.author = _make_user('patchval@example.com', 'patchval1', '+1000004001')
        self.s1 = _spec('A')
        self.s2 = _spec('B')
        self.s3 = _spec('C')
        self.s4 = _spec('D')

        self.client.force_authenticate(user=self.author)
        r = self.client.post(
            reverse('api:questions'),
            {'content': 'orig', 'specializations': [str(self.s1.id)]},
            format='json',
        )
        self.q_id = r.data['id']

    def tearDown(self):
        cache.clear()

    def test_patch_with_more_than_three_specs_400(self):
        res = self.client.patch(
            reverse('api:question-detail', args=[self.q_id]),
            {'specializations': [str(self.s1.id), str(self.s2.id), str(self.s3.id), str(self.s4.id)]},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('specializations', res.data)

    def test_patch_with_zero_specs_400(self):
        res = self.client.patch(
            reverse('api:question-detail', args=[self.q_id]),
            {'specializations': []},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('specializations', res.data)

    def test_patch_with_empty_content_400(self):
        res = self.client.patch(
            reverse('api:question-detail', args=[self.q_id]),
            {'content': '   '},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('content', res.data)

    def test_patch_only_content_keeps_specs(self):
        # Partial update — spec list shouldn't be touched if not sent
        res = self.client.patch(
            reverse('api:question-detail', args=[self.q_id]),
            {'content': 'edited'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['content'], 'edited')
        self.assertEqual(len(res.data['specializations']), 1)

    def test_patch_with_unknown_spec_uuid_400(self):
        import uuid
        res = self.client.patch(
            reverse('api:question-detail', args=[self.q_id]),
            {'specializations': [str(uuid.uuid4())]},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('specializations', res.data)


class FilterCombinationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.alice = _make_user('alice@example.com', 'aliceuser', '+1000005001')
        self.bob = _make_user('bob@example.com', 'bobuser01', '+1000005002')
        self.spec = _spec('Backend')
        self.client.force_authenticate(user=self.alice)

        # Alice: 1 resolved, 1 unresolved
        r1 = self.client.post(
            reverse('api:questions'),
            {'content': 'alice resolved', 'specializations': [str(self.spec.id)]},
            format='json',
        )
        self.client.post(reverse('api:question-resolve', args=[r1.data['id']]))

        self.client.post(
            reverse('api:questions'),
            {'content': 'alice unresolved', 'specializations': [str(self.spec.id)]},
            format='json',
        )

        # Bob: 1 unresolved
        self.client.force_authenticate(user=self.bob)
        self.client.post(
            reverse('api:questions'),
            {'content': 'bob unresolved', 'specializations': [str(self.spec.id)]},
            format='json',
        )

    def tearDown(self):
        cache.clear()

    def test_filter_is_resolved_false(self):
        self.client.force_authenticate(user=self.alice)
        res = self.client.get(reverse('api:questions'), {'is_resolved': 'false'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data['results']), 2)
        for r in res.data['results']:
            self.assertFalse(r['is_resolved'])

    def test_combined_author_and_is_resolved(self):
        self.client.force_authenticate(user=self.alice)
        res = self.client.get(
            reverse('api:questions'),
            {'author': str(self.alice.id), 'is_resolved': 'true'},
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data['results']), 1)
        self.assertTrue(res.data['results'][0]['content_preview'].startswith('alice resolved'))

    def test_garbage_is_resolved_value_silently_returns_all(self):
        self.client.force_authenticate(user=self.alice)
        res = self.client.get(reverse('api:questions'), {'is_resolved': 'banana'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Filter is silently ignored — returns all 3 questions
        self.assertEqual(len(res.data['results']), 3)

    def test_search_returns_empty_when_no_match(self):
        self.client.force_authenticate(user=self.alice)
        res = self.client.get(reverse('api:questions'), {'q': 'no-such-substring-xyz'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data['results']), 0)


class ReplyValidationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.author = _make_user('repval@example.com', 'repvalus', '+1000006001')
        self.spec = _spec('Backend')

        self.client.force_authenticate(user=self.author)
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
        self.a_id = a.data['id']

    def tearDown(self):
        cache.clear()

    def test_reply_with_empty_content_400(self):
        res = self.client.post(
            reverse('api:answer-replies', args=[self.a_id]),
            {'content': '   '},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('content', res.data)

    def test_reply_with_content_too_long_400(self):
        res = self.client.post(
            reverse('api:answer-replies', args=[self.a_id]),
            {'content': 'a' * 5001},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_reply_via_answer_detail_endpoint(self):
        # Replies are stored as Answers; the detail endpoint serves them too
        rep = self.client.post(
            reverse('api:answer-replies', args=[self.a_id]),
            {'content': 'a reply'},
            format='json',
        )
        rep_id = rep.data['id']
        res = self.client.get(reverse('api:answer-detail', args=[rep_id]))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(str(res.data['parent_answer']), self.a_id)
        self.assertEqual(res.data['replies_count'], 0)


class CountConsistencyTests(TestCase):
    """Confirm the Facebook-style answers_count totals top-level + replies, and updates correctly."""

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.asker = _make_user('cc@example.com', 'ccuser01', '+1000007001')
        self.replier = _make_user('cc2@example.com', 'cc2user01', '+1000007002')
        self.spec = _spec('Backend')

        self.client.force_authenticate(user=self.asker)
        q = self.client.post(
            reverse('api:questions'),
            {'content': 'q', 'specializations': [str(self.spec.id)]},
            format='json',
        )
        self.q_id = q.data['id']

    def tearDown(self):
        cache.clear()

    def _detail(self):
        return self.client.get(reverse('api:question-detail', args=[self.q_id]))

    def test_answers_count_starts_at_zero(self):
        self.assertEqual(self._detail().data['answers_count'], 0)

    def test_answers_count_is_facebook_style_total(self):
        # 3 top-level answers + 2 replies under the first
        self.client.force_authenticate(user=self.replier)
        a1 = self.client.post(reverse('api:question-answers', args=[self.q_id]), {'content': 'a1'}, format='json')
        self.client.post(reverse('api:question-answers', args=[self.q_id]), {'content': 'a2'}, format='json')
        self.client.post(reverse('api:question-answers', args=[self.q_id]), {'content': 'a3'}, format='json')
        self.client.post(reverse('api:answer-replies', args=[a1.data['id']]), {'content': 'r1'}, format='json')
        self.client.post(reverse('api:answer-replies', args=[a1.data['id']]), {'content': 'r2'}, format='json')

        self.client.force_authenticate(user=self.asker)
        # 3 answers + 2 replies = 5 total
        self.assertEqual(self._detail().data['answers_count'], 5)

    def test_count_drops_when_top_level_answer_with_replies_is_deleted(self):
        self.client.force_authenticate(user=self.replier)
        a = self.client.post(reverse('api:question-answers', args=[self.q_id]), {'content': 'a'}, format='json')
        self.client.post(reverse('api:answer-replies', args=[a.data['id']]), {'content': 'r1'}, format='json')
        self.client.post(reverse('api:answer-replies', args=[a.data['id']]), {'content': 'r2'}, format='json')

        self.client.force_authenticate(user=self.asker)
        self.assertEqual(self._detail().data['answers_count'], 3)

        # Delete the top-level answer (cascades replies)
        self.client.force_authenticate(user=self.replier)
        self.client.delete(reverse('api:answer-detail', args=[a.data['id']]))

        self.client.force_authenticate(user=self.asker)
        self.assertEqual(self._detail().data['answers_count'], 0)


class SecurityTests(TestCase):
    """Server fills in author/question/parent_answer — client cannot spoof them."""

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.alice = _make_user('sec1@example.com', 'sec1user', '+1000008001')
        self.bob = _make_user('sec2@example.com', 'sec2user', '+1000008002')
        self.spec = _spec('Backend')

    def tearDown(self):
        cache.clear()

    def test_cannot_spoof_author_on_question_create(self):
        # Alice creates a question but tries to claim Bob is the author
        self.client.force_authenticate(user=self.alice)
        res = self.client.post(
            reverse('api:questions'),
            {
                'content': 'q',
                'specializations': [str(self.spec.id)],
                'author': str(self.bob.id),  # Sneaky.
            },
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        # Server ignored the spoofed author field — Alice is on the row
        self.assertEqual(str(res.data['author']['id']), str(self.alice.id))

    def test_cannot_spoof_question_on_answer_create(self):
        # Alice creates question_a, Bob creates question_b
        self.client.force_authenticate(user=self.alice)
        qa = self.client.post(
            reverse('api:questions'),
            {'content': 'qa', 'specializations': [str(self.spec.id)]},
            format='json',
        )
        self.client.force_authenticate(user=self.bob)
        qb = self.client.post(
            reverse('api:questions'),
            {'content': 'qb', 'specializations': [str(self.spec.id)]},
            format='json',
        )

        # Alice posts an answer to qa, but tries to attach it to qb via body
        self.client.force_authenticate(user=self.alice)
        res = self.client.post(
            reverse('api:question-answers', args=[qa.data['id']]),
            {'content': 'a', 'question': qb.data['id']},  # Sneaky — try to redirect
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        # Server used the URL kwarg — answer is on qa, not qb
        self.assertEqual(str(res.data['question']), qa.data['id'])


class EmptyListTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.author = _make_user('empty@example.com', 'emptyusr', '+1000009001')
        self.spec = _spec('Backend')
        self.client.force_authenticate(user=self.author)
        q = self.client.post(
            reverse('api:questions'),
            {'content': 'q', 'specializations': [str(self.spec.id)]},
            format='json',
        )
        self.q_id = q.data['id']
        a = self.client.post(
            reverse('api:question-answers', args=[self.q_id]),
            {'content': 'a'},
            format='json',
        )
        self.a_id = a.data['id']

    def tearDown(self):
        cache.clear()

    def test_list_answers_under_question_with_no_answers(self):
        # Create another question with zero answers
        q = self.client.post(
            reverse('api:questions'),
            {'content': 'empty q', 'specializations': [str(self.spec.id)]},
            format='json',
        )
        res = self.client.get(reverse('api:question-answers', args=[q.data['id']]))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['count'], 0)
        self.assertEqual(len(res.data['results']), 0)

    def test_list_replies_under_answer_with_no_replies(self):
        res = self.client.get(reverse('api:answer-replies', args=[self.a_id]))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['count'], 0)
        self.assertEqual(len(res.data['results']), 0)

    def test_list_questions_when_none_exist(self):
        # Wipe and check
        Question.objects.all().delete()
        res = self.client.get(reverse('api:questions'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['count'], 0)
        self.assertEqual(len(res.data['results']), 0)


class ResolvedAtTimestampTests(TestCase):
    """Confirm resolved_at is set/cleared correctly."""

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.asker = _make_user('rt@example.com', 'rtuser01', '+1000010001')
        self.spec = _spec('Backend')
        self.client.force_authenticate(user=self.asker)
        q = self.client.post(
            reverse('api:questions'),
            {'content': 'q', 'specializations': [str(self.spec.id)]},
            format='json',
        )
        self.q_id = q.data['id']

    def tearDown(self):
        cache.clear()

    def test_resolved_at_starts_null(self):
        res = self.client.get(reverse('api:question-detail', args=[self.q_id]))
        self.assertIsNone(res.data['resolved_at'])

    def test_resolved_at_set_after_resolve(self):
        res = self.client.post(reverse('api:question-resolve', args=[self.q_id]))
        self.assertIsNotNone(res.data['resolved_at'])

    def test_resolved_at_cleared_after_unresolve(self):
        self.client.post(reverse('api:question-resolve', args=[self.q_id]))
        res = self.client.post(reverse('api:question-unresolve', args=[self.q_id]))
        self.assertIsNone(res.data['resolved_at'])
