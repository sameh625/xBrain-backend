"""Tests for Sprint 2 — Item 2: Posts + likes/dislikes.

Posts mirror the Question shape (no resolve flag) and add a per-user
like/dislike reaction system."""

from django.test import TestCase
from django.urls import reverse
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APIClient

from .models import User, Specialization, Post, PostReaction


def _make_user(email, username, phone):
    return User.objects.create_user(
        email=email,
        username=username,
        password='PostPass123!',
        first_name='P',
        last_name='User',
        phone_number=phone,
    )


def _spec(name='Backend'):
    return Specialization.objects.get_or_create(name=name, defaults={'description': ''})[0]


class PostCRUDTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.alice = _make_user('palice@example.com', 'palice01', '+1200000001')
        self.bob = _make_user('pbob@example.com', 'pbob01', '+1200000002')
        self.s_backend = _spec('Backend')
        self.s_ml = _spec('ML')
        self.s_frontend = _spec('Frontend')
        self.s_devops = _spec('DevOps')

    def tearDown(self):
        cache.clear()

    def _create_post(self, author=None, content='A useful tip', spec_ids=None):
        author = author or self.alice
        spec_ids = spec_ids if spec_ids is not None else [str(self.s_backend.id)]
        self.client.force_authenticate(user=author)
        return self.client.post(
            reverse('api:posts'),
            {'content': content, 'specializations': spec_ids},
            format='json',
        )

    def test_create_requires_auth(self):
        self.client.force_authenticate(user=None)
        res = self.client.post(
            reverse('api:posts'),
            {'content': 'hi', 'specializations': [str(self.s_backend.id)]},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_returns_zero_initial_counts(self):
        res = self._create_post()
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        # Brand-new posts have ZERO likes/dislikes/comments and the author has
        # no reaction (they didn't react to their own post).
        self.assertEqual(res.data['likes_count'], 0)
        self.assertEqual(res.data['dislikes_count'], 0)
        self.assertIsNone(res.data['my_reaction'])
        self.assertEqual(res.data['comments_count'], 0)

    def test_create_with_three_specs(self):
        res = self._create_post(
            spec_ids=[str(self.s_backend.id), str(self.s_ml.id), str(self.s_frontend.id)]
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertEqual(len(res.data['specializations']), 3)

    def test_create_with_more_than_three_specs_400(self):
        res = self._create_post(
            spec_ids=[
                str(self.s_backend.id),
                str(self.s_ml.id),
                str(self.s_frontend.id),
                str(self.s_devops.id),
            ]
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_with_zero_specs_400(self):
        res = self._create_post(spec_ids=[])
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_with_empty_content_400(self):
        res = self._create_post(content='   ')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_with_content_too_long_400(self):
        res = self._create_post(content='a' * 5001)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_paginated_newest_first(self):
        self._create_post(content='oldest')
        self._create_post(content='middle')
        self._create_post(content='newest')
        self.client.force_authenticate(user=self.bob)
        res = self.client.get(reverse('api:posts'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        results = res.data['results']
        self.assertEqual(len(results), 3)
        self.assertTrue(results[0]['content_preview'].startswith('newest'))

    def test_filter_by_author(self):
        self._create_post(author=self.alice, content='alice post')
        self._create_post(author=self.bob, content='bob post')
        self.client.force_authenticate(user=self.alice)
        res = self.client.get(reverse('api:posts'), {'author': str(self.alice.id)})
        self.assertEqual(len(res.data['results']), 1)

    def test_search_by_q(self):
        self._create_post(content='How to deploy Django on Azure')
        self._create_post(content='Best ML libraries')
        self.client.force_authenticate(user=self.alice)
        res = self.client.get(reverse('api:posts'), {'q': 'Azure'})
        self.assertEqual(len(res.data['results']), 1)

    def test_anonymous_can_read(self):
        self._create_post(content='public')
        self.client.force_authenticate(user=None)
        res = self.client.get(reverse('api:posts'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Anonymous viewer → my_reaction is null
        self.assertIsNone(res.data['results'][0]['my_reaction'])

    def test_patch_post_author_only(self):
        r = self._create_post()
        post_id = r.data['id']

        self.client.force_authenticate(user=self.alice)
        res = self.client.patch(
            reverse('api:post-detail', args=[post_id]),
            {'content': 'edited'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(user=self.bob)
        res = self.client.patch(
            reverse('api:post-detail', args=[post_id]),
            {'content': 'hacked'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_post_cascades_reactions(self):
        r = self._create_post()
        post_id = r.data['id']

        # Bob likes it
        self.client.force_authenticate(user=self.bob)
        self.client.post(reverse('api:post-like', args=[post_id]))
        self.assertEqual(PostReaction.objects.filter(post_id=post_id).count(), 1)

        # Alice deletes the post → reactions should cascade
        self.client.force_authenticate(user=self.alice)
        res = self.client.delete(reverse('api:post-detail', args=[post_id]))
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(PostReaction.objects.filter(post_id=post_id).count(), 0)


class PostReactionTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.alice = _make_user('ralice@example.com', 'ralice01', '+1200000003')
        self.bob = _make_user('rbob@example.com', 'rbob01', '+1200000004')
        self.carol = _make_user('rcarol@example.com', 'rcarol01', '+1200000005')
        self.spec = _spec('Backend')

        # Alice creates a post
        self.client.force_authenticate(user=self.alice)
        r = self.client.post(
            reverse('api:posts'),
            {'content': 'Alice post', 'specializations': [str(self.spec.id)]},
            format='json',
        )
        self.post_id = r.data['id']

    def tearDown(self):
        cache.clear()

    def test_anon_cannot_react(self):
        self.client.force_authenticate(user=None)
        res = self.client.post(reverse('api:post-like', args=[self.post_id]))
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_like_a_post(self):
        self.client.force_authenticate(user=self.bob)
        res = self.client.post(reverse('api:post-like', args=[self.post_id]))
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.assertEqual(res.data['likes_count'], 1)
        self.assertEqual(res.data['dislikes_count'], 0)
        self.assertEqual(res.data['my_reaction'], 'like')

    def test_like_then_like_toggles_off(self):
        self.client.force_authenticate(user=self.bob)
        # First like
        self.client.post(reverse('api:post-like', args=[self.post_id]))
        # Second like → toggle off
        res = self.client.post(reverse('api:post-like', args=[self.post_id]))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['likes_count'], 0)
        self.assertIsNone(res.data['my_reaction'])

    def test_like_then_dislike_switches(self):
        self.client.force_authenticate(user=self.bob)
        self.client.post(reverse('api:post-like', args=[self.post_id]))
        res = self.client.post(reverse('api:post-dislike', args=[self.post_id]))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Switched: like gone, dislike added — total reactions still 1
        self.assertEqual(res.data['likes_count'], 0)
        self.assertEqual(res.data['dislikes_count'], 1)
        self.assertEqual(res.data['my_reaction'], 'dislike')
        self.assertEqual(PostReaction.objects.filter(post_id=self.post_id, user=self.bob).count(), 1)

    def test_dislike_then_dislike_toggles_off(self):
        self.client.force_authenticate(user=self.bob)
        self.client.post(reverse('api:post-dislike', args=[self.post_id]))
        res = self.client.post(reverse('api:post-dislike', args=[self.post_id]))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['dislikes_count'], 0)
        self.assertIsNone(res.data['my_reaction'])

    def test_two_users_like_independently(self):
        self.client.force_authenticate(user=self.bob)
        self.client.post(reverse('api:post-like', args=[self.post_id]))
        self.client.force_authenticate(user=self.carol)
        res = self.client.post(reverse('api:post-like', args=[self.post_id]))
        self.assertEqual(res.data['likes_count'], 2)
        # Carol sees her own reaction
        self.assertEqual(res.data['my_reaction'], 'like')

    def test_anonymous_viewer_sees_null_my_reaction(self):
        # Bob likes
        self.client.force_authenticate(user=self.bob)
        self.client.post(reverse('api:post-like', args=[self.post_id]))

        # Anonymous reader sees the count but not a personal reaction
        self.client.force_authenticate(user=None)
        res = self.client.get(reverse('api:post-detail', args=[self.post_id]))
        self.assertEqual(res.data['likes_count'], 1)
        self.assertIsNone(res.data['my_reaction'])

    def test_unique_constraint_one_reaction_per_user_per_post(self):
        """A user can never have both a like and a dislike on the same post —
        the unique_together constraint enforces this at the DB level."""
        self.client.force_authenticate(user=self.bob)
        self.client.post(reverse('api:post-like', args=[self.post_id]))
        self.client.post(reverse('api:post-dislike', args=[self.post_id]))
        # Only ONE reaction row, even after toggling between the two
        rows = PostReaction.objects.filter(user=self.bob, post_id=self.post_id)
        self.assertEqual(rows.count(), 1)
        self.assertEqual(rows.first().reaction, 'dislike')

    def test_react_to_nonexistent_post_404(self):
        import uuid
        self.client.force_authenticate(user=self.bob)
        res = self.client.post(reverse('api:post-like', args=[uuid.uuid4()]))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_reactions_cascade_when_user_deleted(self):
        self.client.force_authenticate(user=self.bob)
        self.client.post(reverse('api:post-like', args=[self.post_id]))
        self.assertEqual(PostReaction.objects.filter(user=self.bob).count(), 1)

        self.bob.delete()
        self.assertEqual(PostReaction.objects.filter(post_id=self.post_id).count(), 0)

    def test_self_reaction_allowed(self):
        # Alice (the author) can react to her own post.
        self.client.force_authenticate(user=self.alice)
        res = self.client.post(reverse('api:post-like', args=[self.post_id]))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['my_reaction'], 'like')
