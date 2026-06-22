"""Tests for Sprint 4: Reward Points on Questions + Ranked Feed + Seen Tracking.

The points flow uses the existing meeting-request endpoints; we don't hit
Google Calendar at all here because booking is done at REQUEST time (not at
accept). For the resolve tests we synthesize a SCHEDULED MeetingRequest
directly via the ORM and stub `now()` past its `scheduled_at`.
"""

from datetime import timedelta
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from .models import (
    Answer, MeetingRequest, PointsWallet, Post, Question,
    SeenPost, SeenQuestion, Specialization, User, UserSpecialization,
)
from .utils import (
    QUESTION_EXTRA_SPEC_BONUS, W_SEEN, W_SPEC, compute_question_cost,
)


def _make_user(email, username, phone, specs=None, balance=None):
    """Create a user; signal auto-creates wallet at 50 points (signup bonus).
    Pass `balance` to override the wallet balance after creation."""
    u = User.objects.create_user(
        email=email, username=username, password='TestPass123!',
        first_name='T', last_name='User', phone_number=phone,
    )
    if balance is not None:
        u.wallet.balance = balance
        u.wallet.save(update_fields=['balance'])
    if specs:
        for s in specs:
            UserSpecialization.objects.create(user=u, specialization=s)
    return u


def _spec(name, points=10):
    return Specialization.objects.create(name=name, description='', points=points)


# ════════════════════════════════════════════════════════════════════════════
#  Reward points: cost formula
# ════════════════════════════════════════════════════════════════════════════


class CostFormulaTests(TestCase):
    """Pure unit tests on compute_question_cost — no DB writes needed beyond setUp."""

    def setUp(self):
        cache.clear()
        self.s10 = _spec('S10', points=10)
        self.s50 = _spec('S50', points=50)
        self.s80 = _spec('S80', points=80)

    def test_single_spec_cost_is_just_spec_points(self):
        self.assertEqual(compute_question_cost([self.s50]), 50)

    def test_two_specs_takes_max_plus_one_bonus(self):
        self.assertEqual(
            compute_question_cost([self.s10, self.s50]),
            50 + QUESTION_EXTRA_SPEC_BONUS,
        )

    def test_three_specs_takes_max_plus_two_bonuses(self):
        self.assertEqual(
            compute_question_cost([self.s10, self.s50, self.s80]),
            80 + 2 * QUESTION_EXTRA_SPEC_BONUS,
        )

    def test_empty_list_is_zero(self):
        self.assertEqual(compute_question_cost([]), 0)


# ════════════════════════════════════════════════════════════════════════════
#  Signup bonus (signal-driven)
# ════════════════════════════════════════════════════════════════════════════


class SignupBonusTests(TestCase):
    def test_new_user_wallet_starts_at_fifty(self):
        u = User.objects.create_user(
            email='new@example.com', username='newuser1', password='TestPass123!',
            first_name='N', last_name='U', phone_number='+1900000099',
        )
        self.assertEqual(u.wallet.balance, 50)


# ════════════════════════════════════════════════════════════════════════════
#  Reward points: request-meeting books points
# ════════════════════════════════════════════════════════════════════════════


class RequestMeetingBookingTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.s_backend = _spec('Backend', points=40)
        self.s_ml = _spec('ML', points=70)
        self.asker = _make_user('asker@e.com', 'askeruser', '+1000000001', balance=200)
        self.answerer = _make_user('ans@e.com', 'ansuser', '+1000000002', balance=0)
        self.q = Question.objects.create(author=self.asker, content='hi?')
        self.q.specializations.set([self.s_backend, self.s_ml])
        self.a = Answer.objects.create(question=self.q, author=self.answerer, content='try X')
        self.expected_cost = 70 + QUESTION_EXTRA_SPEC_BONUS  # 75

    def _post_request_meeting(self, answer_id=None, asker=None):
        self.client.force_authenticate(user=asker or self.asker)
        return self.client.post(
            reverse('api:request-meeting', kwargs={'pk': answer_id or self.a.id}),
            {
                'duration_minutes': 30,
                'proposed_slots': [
                    (timezone.now() + timedelta(hours=24)).isoformat(),
                ],
                'message': '',
            },
            format='json',
        )

    def test_request_books_cost_and_blocks_question(self):
        res = self._post_request_meeting()
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.q.refresh_from_db()
        self.assertTrue(self.q.is_blocked)
        self.assertEqual(self.q.booked_amount, self.expected_cost)
        self.assertEqual(self.q.answerer_id, self.answerer.id)

    def test_request_with_insufficient_balance_returns_402(self):
        self.asker.wallet.balance = self.expected_cost - 1
        self.asker.wallet.save()
        res = self._post_request_meeting()
        self.assertEqual(res.status_code, status.HTTP_402_PAYMENT_REQUIRED, res.data)
        self.assertEqual(res.data['required'], self.expected_cost)
        self.q.refresh_from_db()
        self.assertFalse(self.q.is_blocked)

    def test_request_on_already_blocked_question_returns_400(self):
        # First request succeeds, blocks the question.
        first = self._post_request_meeting()
        self.assertEqual(first.status_code, status.HTTP_201_CREATED, first.data)
        # A second answer on the same question, second request → 400.
        other_answerer = _make_user('a2@e.com', 'a2user', '+1000000003')
        a2 = Answer.objects.create(question=self.q, author=other_answerer, content='or Y')
        res = self._post_request_meeting(answer_id=a2.id)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST, res.data)
        # Block still held by the first meet.
        self.q.refresh_from_db()
        self.assertTrue(self.q.is_blocked)
        self.assertEqual(self.q.booked_amount, self.expected_cost)


# ════════════════════════════════════════════════════════════════════════════
#  available_balance — multi-question scenarios
# ════════════════════════════════════════════════════════════════════════════


class AvailableBalanceTests(TestCase):
    def setUp(self):
        cache.clear()
        self.s = _spec('S', points=30)
        self.u = _make_user('u@e.com', 'uuser1234', '+1000010001', balance=100)

    def test_available_subtracts_only_blocked_not_transferred(self):
        # Two questions, both blocked, one already transferred.
        q1 = Question.objects.create(
            author=self.u, content='q1', is_blocked=True, booked_amount=20,
            answerer=self.u,
        )
        q1.specializations.set([self.s])
        q2 = Question.objects.create(
            author=self.u, content='q2', is_blocked=True, booked_amount=10,
            answerer=self.u, is_transferred=True,
        )
        q2.specializations.set([self.s])
        self.assertEqual(self.u.available_balance, 100 - 20)  # only q1 counts


# ════════════════════════════════════════════════════════════════════════════
#  Edit / delete guards while blocked
# ════════════════════════════════════════════════════════════════════════════


class BlockedQuestionGuardTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.s = _spec('S', points=20)
        self.asker = _make_user('a@e.com', 'askeruser', '+1000020001', balance=100)
        self.answerer = _make_user('b@e.com', 'ansuser1', '+1000020002')
        self.q = Question.objects.create(
            author=self.asker, content='locked one',
            is_blocked=True, booked_amount=20, answerer=self.answerer,
        )
        self.q.specializations.set([self.s])

    def test_patch_blocked_question_returns_400(self):
        self.client.force_authenticate(user=self.asker)
        res = self.client.patch(
            reverse('api:question-detail', kwargs={'pk': self.q.id}),
            {'content': 'new content'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST, res.data)

    def test_delete_blocked_question_returns_400(self):
        self.client.force_authenticate(user=self.asker)
        res = self.client.delete(
            reverse('api:question-detail', kwargs={'pk': self.q.id}),
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST, res.data)


# ════════════════════════════════════════════════════════════════════════════
#  Decline / cancel release the booking
# ════════════════════════════════════════════════════════════════════════════


class BookingReleaseTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.s = _spec('S', points=25)
        self.asker = _make_user('a@e.com', 'askeruser', '+1000030001', balance=100)
        self.answerer = _make_user('b@e.com', 'ansuser1', '+1000030002')
        self.q = Question.objects.create(author=self.asker, content='?')
        self.q.specializations.set([self.s])
        self.a = Answer.objects.create(question=self.q, author=self.answerer, content='!')
        self.mr = MeetingRequest.objects.create(
            answer=self.a, asker=self.asker, answerer=self.answerer,
            duration_minutes=30,
            proposed_slots=[timezone.now() + timedelta(hours=24)],
            status=MeetingRequest.STATUS_PENDING,
        )
        # Hand-block so we don't need to go through the request endpoint.
        self.q.is_blocked = True
        self.q.booked_amount = 25
        self.q.answerer = self.answerer
        self.q.save()

    def test_decline_releases_booking(self):
        self.client.force_authenticate(user=self.answerer)
        res = self.client.post(
            reverse('api:decline-meeting', kwargs={'pk': self.mr.id}),
            {'message': 'busy'}, format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.q.refresh_from_db()
        self.assertFalse(self.q.is_blocked)
        self.assertEqual(self.q.booked_amount, 0)
        self.assertIsNone(self.q.answerer)

    def test_cancel_pending_releases_booking(self):
        self.client.force_authenticate(user=self.asker)
        res = self.client.post(
            reverse('api:cancel-meeting', kwargs={'pk': self.mr.id}),
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.q.refresh_from_db()
        self.assertFalse(self.q.is_blocked)
        self.assertEqual(self.q.booked_amount, 0)

    @patch('api.google_meet.cancel_meet_event')
    def test_cancel_scheduled_releases_booking_and_cancels_calendar(self, mock_cancel_event):
        self.mr.status = MeetingRequest.STATUS_SCHEDULED
        self.mr.scheduled_at = timezone.now() + timedelta(hours=24)
        self.mr.google_event_id = 'fake-event-id'
        self.mr.save()

        self.client.force_authenticate(user=self.asker)
        res = self.client.post(
            reverse('api:cancel-meeting', kwargs={'pk': self.mr.id}),
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        mock_cancel_event.assert_called_once_with('fake-event-id')
        self.q.refresh_from_db()
        self.assertFalse(self.q.is_blocked)


# ════════════════════════════════════════════════════════════════════════════
#  Resolve: point transfer, time-gate, idempotency, unresolve guard
# ════════════════════════════════════════════════════════════════════════════


class ResolveTransferTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.s = _spec('S', points=30)
        self.asker = _make_user('a@e.com', 'askeruser', '+1000040001', balance=100)
        self.answerer = _make_user('b@e.com', 'ansuser1', '+1000040002', balance=10)
        self.q = Question.objects.create(
            author=self.asker, content='?',
            is_blocked=True, booked_amount=30, answerer=self.answerer,
        )
        self.q.specializations.set([self.s])
        self.a = Answer.objects.create(question=self.q, author=self.answerer, content='!')

    def _make_scheduled_meet(self, scheduled_at):
        return MeetingRequest.objects.create(
            answer=self.a, asker=self.asker, answerer=self.answerer,
            duration_minutes=30,
            proposed_slots=[scheduled_at],
            scheduled_at=scheduled_at,
            status=MeetingRequest.STATUS_SCHEDULED,
        )

    def test_resolve_without_scheduled_meet_returns_400(self):
        # Question is blocked but there's no scheduled meet.
        self.client.force_authenticate(user=self.asker)
        res = self.client.post(reverse('api:question-resolve', kwargs={'pk': self.q.id}))
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST, res.data)

    def test_resolve_before_meet_time_returns_400(self):
        self._make_scheduled_meet(timezone.now() + timedelta(hours=2))
        self.client.force_authenticate(user=self.asker)
        res = self.client.post(reverse('api:question-resolve', kwargs={'pk': self.q.id}))
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST, res.data)

    def test_resolve_after_meet_time_transfers_points(self):
        self._make_scheduled_meet(timezone.now() - timedelta(hours=1))
        self.client.force_authenticate(user=self.asker)
        res = self.client.post(reverse('api:question-resolve', kwargs={'pk': self.q.id}))
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.asker.wallet.refresh_from_db()
        self.answerer.wallet.refresh_from_db()
        self.assertEqual(self.asker.wallet.balance, 100 - 30)
        self.assertEqual(self.answerer.wallet.balance, 10 + 30)
        self.q.refresh_from_db()
        self.assertTrue(self.q.is_resolved)
        self.assertTrue(self.q.is_transferred)

    def test_resolve_is_idempotent_after_transfer(self):
        self._make_scheduled_meet(timezone.now() - timedelta(hours=1))
        self.client.force_authenticate(user=self.asker)
        self.client.post(reverse('api:question-resolve', kwargs={'pk': self.q.id}))
        # Second call must not double-transfer.
        self.client.post(reverse('api:question-resolve', kwargs={'pk': self.q.id}))
        self.asker.wallet.refresh_from_db()
        self.answerer.wallet.refresh_from_db()
        self.assertEqual(self.asker.wallet.balance, 100 - 30)
        self.assertEqual(self.answerer.wallet.balance, 10 + 30)

    def test_unresolve_after_transfer_returns_400(self):
        self._make_scheduled_meet(timezone.now() - timedelta(hours=1))
        self.client.force_authenticate(user=self.asker)
        self.client.post(reverse('api:question-resolve', kwargs={'pk': self.q.id}))
        res = self.client.post(reverse('api:question-unresolve', kwargs={'pk': self.q.id}))
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST, res.data)


# ════════════════════════════════════════════════════════════════════════════
#  Ranked feed
# ════════════════════════════════════════════════════════════════════════════


class RankedFeedTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.s_backend = _spec('Backend', points=40)
        self.s_frontend = _spec('Frontend', points=20)
        self.viewer = _make_user(
            'v@e.com', 'vieweruser', '+1000050001', specs=[self.s_backend],
        )
        self.other = _make_user('o@e.com', 'otheruser', '+1000050002')

    def test_authenticated_viewer_sees_matching_spec_first(self):
        # Create three posts at near-identical timestamps.
        p_match = Post.objects.create(author=self.other, content='backend post')
        p_match.specializations.set([self.s_backend])
        p_offtopic = Post.objects.create(author=self.other, content='frontend post')
        p_offtopic.specializations.set([self.s_frontend])
        p_match_seen = Post.objects.create(author=self.other, content='already seen backend')
        p_match_seen.specializations.set([self.s_backend])
        SeenPost.objects.create(user=self.viewer, post=p_match_seen)

        self.client.force_authenticate(user=self.viewer)
        res = self.client.get(reverse('api:posts'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ordered_ids = [r['id'] for r in res.data['results']]
        # Matching + unseen first.
        self.assertEqual(ordered_ids[0], str(p_match.id))
        # Seen items should rank below their unseen matching peer.
        self.assertLess(
            ordered_ids.index(str(p_match.id)),
            ordered_ids.index(str(p_match_seen.id)),
        )

    def test_anonymous_viewer_gets_newest_first(self):
        old = Post.objects.create(author=self.other, content='old')
        old.specializations.set([self.s_backend])
        # Force `created_at` to be older — auto_now_add prevents direct set on create,
        # so update afterward.
        Post.objects.filter(pk=old.pk).update(
            created_at=timezone.now() - timedelta(days=2),
        )
        recent = Post.objects.create(author=self.other, content='recent')
        recent.specializations.set([self.s_frontend])

        self.client.force_authenticate(user=None)
        res = self.client.get(reverse('api:posts'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ordered_ids = [r['id'] for r in res.data['results']]
        self.assertEqual(ordered_ids[0], str(recent.id))
        self.assertEqual(ordered_ids[1], str(old.id))

    def test_questions_feed_is_also_ranked_for_authenticated_viewers(self):
        q_match = Question.objects.create(author=self.other, content='backend q')
        q_match.specializations.set([self.s_backend])
        q_off = Question.objects.create(author=self.other, content='frontend q')
        q_off.specializations.set([self.s_frontend])

        self.client.force_authenticate(user=self.viewer)
        res = self.client.get(reverse('api:questions'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ordered_ids = [r['id'] for r in res.data['results']]
        self.assertEqual(ordered_ids[0], str(q_match.id))


# ════════════════════════════════════════════════════════════════════════════
#  Mark-seen endpoints
# ════════════════════════════════════════════════════════════════════════════


class MarkSeenEndpointTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.s = _spec('S', points=20)
        self.viewer = _make_user('v@e.com', 'vieweruser', '+1000060001')
        self.other = _make_user('o@e.com', 'otheruser', '+1000060002')

    def test_mark_posts_seen_creates_rows(self):
        p1 = Post.objects.create(author=self.other, content='one')
        p1.specializations.set([self.s])
        p2 = Post.objects.create(author=self.other, content='two')
        p2.specializations.set([self.s])

        self.client.force_authenticate(user=self.viewer)
        res = self.client.post(
            reverse('api:posts-mark-seen'),
            {'post_ids': [str(p1.id), str(p2.id)]},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT, res.data)
        self.assertEqual(
            SeenPost.objects.filter(user=self.viewer, post__in=[p1, p2]).count(),
            2,
        )

    def test_mark_posts_seen_is_idempotent(self):
        p = Post.objects.create(author=self.other, content='one')
        p.specializations.set([self.s])
        self.client.force_authenticate(user=self.viewer)
        self.client.post(
            reverse('api:posts-mark-seen'),
            {'post_ids': [str(p.id)]}, format='json',
        )
        self.client.post(
            reverse('api:posts-mark-seen'),
            {'post_ids': [str(p.id)]}, format='json',
        )
        self.assertEqual(SeenPost.objects.filter(user=self.viewer).count(), 1)

    def test_mark_posts_seen_ignores_unknown_ids(self):
        self.client.force_authenticate(user=self.viewer)
        import uuid
        res = self.client.post(
            reverse('api:posts-mark-seen'),
            {'post_ids': [str(uuid.uuid4())]},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(SeenPost.objects.count(), 0)

    def test_mark_posts_seen_empty_list_returns_400(self):
        self.client.force_authenticate(user=self.viewer)
        res = self.client.post(
            reverse('api:posts-mark-seen'),
            {'post_ids': []}, format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_mark_posts_seen_requires_auth(self):
        res = self.client.post(reverse('api:posts-mark-seen'), {'post_ids': []}, format='json')
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_mark_questions_seen_creates_rows(self):
        q = Question.objects.create(author=self.other, content='?')
        q.specializations.set([self.s])
        self.client.force_authenticate(user=self.viewer)
        res = self.client.post(
            reverse('api:questions-mark-seen'),
            {'question_ids': [str(q.id)]}, format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT, res.data)
        self.assertTrue(SeenQuestion.objects.filter(user=self.viewer, question=q).exists())


# ════════════════════════════════════════════════════════════════════════════
#  Auto-seen on feed pagination
# ════════════════════════════════════════════════════════════════════════════


class AutoSeenOnFeedTests(TestCase):
    """The feed endpoints (GET /api/posts/, GET /api/questions/) auto-mark
    every item on the served page as seen for the authenticated viewer.
    Profile lists (/users/me/posts/) and anonymous requests do NOT."""

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.s = _spec('S', points=20)
        self.viewer = _make_user(
            'v@e.com', 'vieweruser', '+1000070001', specs=[self.s],
        )
        self.other = _make_user('o@e.com', 'otheruser', '+1000070002')

    def _make_post(self, content):
        p = Post.objects.create(author=self.other, content=content)
        p.specializations.set([self.s])
        return p

    def _make_question(self, content):
        q = Question.objects.create(author=self.other, content=content)
        q.specializations.set([self.s])
        return q

    def test_get_posts_feed_auto_marks_returned_items_seen(self):
        posts = [self._make_post(f'post {i}') for i in range(3)]
        self.client.force_authenticate(user=self.viewer)
        res = self.client.get(reverse('api:posts'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        returned_ids = {r['id'] for r in res.data['results']}
        seen_ids = set(
            SeenPost.objects.filter(user=self.viewer).values_list('post_id', flat=True)
        )
        self.assertEqual({str(pid) for pid in seen_ids}, returned_ids)
        self.assertEqual(len(seen_ids), len(posts))

    def test_get_questions_feed_auto_marks_returned_items_seen(self):
        questions = [self._make_question(f'q {i}') for i in range(3)]
        self.client.force_authenticate(user=self.viewer)
        res = self.client.get(reverse('api:questions'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        returned_ids = {r['id'] for r in res.data['results']}
        seen_ids = set(
            SeenQuestion.objects.filter(user=self.viewer).values_list('question_id', flat=True)
        )
        self.assertEqual({str(qid) for qid in seen_ids}, returned_ids)
        self.assertEqual(len(seen_ids), len(questions))

    def test_anonymous_feed_request_does_not_create_seen_rows(self):
        self._make_post('anon visible')
        self.client.force_authenticate(user=None)
        res = self.client.get(reverse('api:posts'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(SeenPost.objects.count(), 0)

    def test_profile_posts_view_does_not_mark_seen(self):
        # Viewer's own post; profile list should never auto-mark seen.
        own = Post.objects.create(author=self.viewer, content='mine')
        own.specializations.set([self.s])
        self.client.force_authenticate(user=self.viewer)
        res = self.client.get(reverse('api:my-posts'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(SeenPost.objects.filter(user=self.viewer).count(), 0)

    def test_feed_auto_seen_is_idempotent(self):
        post = self._make_post('once')
        self.client.force_authenticate(user=self.viewer)
        self.client.get(reverse('api:posts'))
        self.client.get(reverse('api:posts'))
        # No IntegrityError from the unique_together, and only one row exists.
        self.assertEqual(
            SeenPost.objects.filter(user=self.viewer, post=post).count(), 1,
        )

    def test_feed_returns_at_most_10_items_per_page(self):
        # PAGE_SIZE is 10. 15 posts → page 1 has 10, page 2 has 5.
        for i in range(15):
            self._make_post(f'p{i}')
        self.client.force_authenticate(user=self.viewer)

        res1 = self.client.get(reverse('api:posts'))
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res1.data['results']), 10)
        self.assertEqual(res1.data['count'], 15)

        res2 = self.client.get(reverse('api:posts'), {'page': 2})
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res2.data['results']), 5)
