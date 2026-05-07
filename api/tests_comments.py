"""Tests for Sprint 2 — Item 3: Comments + replies on Posts.

Same shape as Q&A's Answer + Reply. Differences:
- No attachments on comments.
- No resolve flag.
- Post-author can ALSO delete comments (light moderation), in addition to
  the comment's own author."""

from django.test import TestCase
from django.urls import reverse
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APIClient

from .models import User, Specialization, Post, Comment


def _make_user(email, username, phone):
    return User.objects.create_user(
        email=email,
        username=username,
        password='CommentPass123!',
        first_name='C',
        last_name='User',
        phone_number=phone,
    )


def _spec(name='Backend'):
    return Specialization.objects.get_or_create(name=name, defaults={'description': ''})[0]


class CommentTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.author = _make_user('cauthor@example.com', 'cauthor01', '+1600000001')
        self.commenter = _make_user('ccmtr@example.com', 'ccmtr01', '+1600000002')
        self.other = _make_user('cother@example.com', 'cother01', '+1600000003')
        self.spec = _spec('Backend')

        # Author creates a post
        self.client.force_authenticate(user=self.author)
        r = self.client.post(
            reverse('api:posts'),
            {'content': 'Post for comments', 'specializations': [str(self.spec.id)]},
            format='json',
        )
        self.post_id = r.data['id']

    def tearDown(self):
        cache.clear()

    # --- Top-level comments ---

    def test_post_comment_requires_auth(self):
        self.client.force_authenticate(user=None)
        res = self.client.post(
            reverse('api:post-comments', args=[self.post_id]),
            {'content': 'a comment'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_post_top_level_comment(self):
        self.client.force_authenticate(user=self.commenter)
        res = self.client.post(
            reverse('api:post-comments', args=[self.post_id]),
            {'content': 'great post'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertEqual(str(res.data['post']), self.post_id)
        self.assertIsNone(res.data['parent_comment'])
        self.assertEqual(res.data['replies_count'], 0)

    def test_self_comment_allowed(self):
        # Post author can comment on their own post.
        self.client.force_authenticate(user=self.author)
        res = self.client.post(
            reverse('api:post-comments', args=[self.post_id]),
            {'content': 'thanks for reading'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_list_top_level_comments_excludes_replies(self):
        self.client.force_authenticate(user=self.commenter)
        c1 = self.client.post(
            reverse('api:post-comments', args=[self.post_id]),
            {'content': 'c1'}, format='json',
        )
        # Add a reply
        self.client.post(
            reverse('api:comment-replies', args=[c1.data['id']]),
            {'content': 'reply'}, format='json',
        )

        res = self.client.get(reverse('api:post-comments', args=[self.post_id]))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Only 1 result — replies don't leak into top-level list
        self.assertEqual(len(res.data['results']), 1)

    def test_post_comment_to_nonexistent_post_404(self):
        import uuid
        self.client.force_authenticate(user=self.commenter)
        res = self.client.post(
            reverse('api:post-comments', args=[uuid.uuid4()]),
            {'content': 'x'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_comment_with_empty_content_400(self):
        self.client.force_authenticate(user=self.commenter)
        res = self.client.post(
            reverse('api:post-comments', args=[self.post_id]),
            {'content': '   '},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    # --- Edit ---

    def test_patch_comment_author_only(self):
        self.client.force_authenticate(user=self.commenter)
        c = self.client.post(
            reverse('api:post-comments', args=[self.post_id]),
            {'content': 'orig'}, format='json',
        )
        c_id = c.data['id']

        # Author edits their own comment
        res = self.client.patch(
            reverse('api:comment-detail', args=[c_id]),
            {'content': 'edited'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Random user cannot edit
        self.client.force_authenticate(user=self.other)
        res = self.client.patch(
            reverse('api:comment-detail', args=[c_id]),
            {'content': 'hacked'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # Post-author also cannot EDIT (only delete) — moderation power is delete-only
        self.client.force_authenticate(user=self.author)
        res = self.client.patch(
            reverse('api:comment-detail', args=[c_id]),
            {'content': 'mod-edited'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    # --- Delete ---

    def test_delete_by_comment_author(self):
        self.client.force_authenticate(user=self.commenter)
        c = self.client.post(
            reverse('api:post-comments', args=[self.post_id]),
            {'content': 'delete me'}, format='json',
        )
        c_id = c.data['id']

        res = self.client.delete(reverse('api:comment-detail', args=[c_id]))
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_by_post_author_moderation(self):
        # Commenter posts a comment on author's post
        self.client.force_authenticate(user=self.commenter)
        c = self.client.post(
            reverse('api:post-comments', args=[self.post_id]),
            {'content': 'spam'}, format='json',
        )
        c_id = c.data['id']

        # Post author moderates by deleting
        self.client.force_authenticate(user=self.author)
        res = self.client.delete(reverse('api:comment-detail', args=[c_id]))
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Comment.objects.filter(id=c_id).exists())

    def test_delete_by_random_user_403(self):
        self.client.force_authenticate(user=self.commenter)
        c = self.client.post(
            reverse('api:post-comments', args=[self.post_id]),
            {'content': 'mine'}, format='json',
        )
        c_id = c.data['id']

        self.client.force_authenticate(user=self.other)
        res = self.client.delete(reverse('api:comment-detail', args=[c_id]))
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_top_level_cascades_replies(self):
        self.client.force_authenticate(user=self.commenter)
        c = self.client.post(
            reverse('api:post-comments', args=[self.post_id]),
            {'content': 'parent'}, format='json',
        )
        c_id = c.data['id']
        # Add 2 replies
        self.client.post(reverse('api:comment-replies', args=[c_id]), {'content': 'r1'}, format='json')
        self.client.post(reverse('api:comment-replies', args=[c_id]), {'content': 'r2'}, format='json')
        self.assertEqual(Comment.objects.filter(parent_comment_id=c_id).count(), 2)

        # Delete the parent
        res = self.client.delete(reverse('api:comment-detail', args=[c_id]))
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Comment.objects.filter(parent_comment_id=c_id).count(), 0)


class CommentReplyTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.author = _make_user('rauthor@example.com', 'rauthor01', '+1600000004')
        self.commenter = _make_user('rcmtr@example.com', 'rcmtr01', '+1600000005')
        self.replier = _make_user('rrep@example.com', 'rrep01', '+1600000006')
        self.spec = _spec('Backend')

        # Post + top-level comment
        self.client.force_authenticate(user=self.author)
        p = self.client.post(
            reverse('api:posts'),
            {'content': 'p', 'specializations': [str(self.spec.id)]},
            format='json',
        )
        self.post_id = p.data['id']

        self.client.force_authenticate(user=self.commenter)
        c = self.client.post(
            reverse('api:post-comments', args=[self.post_id]),
            {'content': 'top-level comment'},
            format='json',
        )
        self.comment_id = c.data['id']

    def tearDown(self):
        cache.clear()

    def test_post_reply_requires_auth(self):
        self.client.force_authenticate(user=None)
        res = self.client.post(
            reverse('api:comment-replies', args=[self.comment_id]),
            {'content': 'r'}, format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_anyone_authenticated_can_reply(self):
        self.client.force_authenticate(user=self.replier)
        res = self.client.post(
            reverse('api:comment-replies', args=[self.comment_id]),
            {'content': 'random reply'}, format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertEqual(str(res.data['parent_comment']), self.comment_id)
        self.assertEqual(str(res.data['post']), self.post_id)

    def test_reply_to_a_reply_400(self):
        # First reply
        self.client.force_authenticate(user=self.replier)
        r1 = self.client.post(
            reverse('api:comment-replies', args=[self.comment_id]),
            {'content': 'first reply'},
            format='json',
        )
        # Try to reply to that reply
        res = self.client.post(
            reverse('api:comment-replies', args=[r1.data['id']]),
            {'content': 'reply to a reply'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('parent_comment', res.data)

    def test_list_replies_under_a_comment(self):
        self.client.force_authenticate(user=self.replier)
        for i in range(3):
            self.client.post(
                reverse('api:comment-replies', args=[self.comment_id]),
                {'content': f'r{i}'},
                format='json',
            )
        res = self.client.get(reverse('api:comment-replies', args=[self.comment_id]))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data['results']), 3)

    def test_reply_with_empty_content_400(self):
        self.client.force_authenticate(user=self.replier)
        res = self.client.post(
            reverse('api:comment-replies', args=[self.comment_id]),
            {'content': '   '},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reply_to_nonexistent_comment_404(self):
        import uuid
        self.client.force_authenticate(user=self.replier)
        res = self.client.post(
            reverse('api:comment-replies', args=[uuid.uuid4()]),
            {'content': 'x'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)


class PostDetailEmbedsCommentsTests(TestCase):
    """Verify PostDetailSerializer embeds first 10 top-level comments
    with first 2 replies each, and that comments_count is the Facebook-style total."""

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.author = _make_user('eauthor@example.com', 'eauthor01', '+1600000007')
        self.commenter = _make_user('ecmtr@example.com', 'ecmtr01', '+1600000008')
        self.spec = _spec('Backend')

        self.client.force_authenticate(user=self.author)
        p = self.client.post(
            reverse('api:posts'),
            {'content': 'embed test', 'specializations': [str(self.spec.id)]},
            format='json',
        )
        self.post_id = p.data['id']

    def tearDown(self):
        cache.clear()

    def test_post_detail_embeds_comments_and_replies(self):
        self.client.force_authenticate(user=self.commenter)
        # 2 top-level comments + 3 replies under the first
        c1 = self.client.post(
            reverse('api:post-comments', args=[self.post_id]),
            {'content': 'c1'}, format='json',
        )
        self.client.post(
            reverse('api:post-comments', args=[self.post_id]),
            {'content': 'c2'}, format='json',
        )
        for i in range(3):
            self.client.post(
                reverse('api:comment-replies', args=[c1.data['id']]),
                {'content': f'r{i}'}, format='json',
            )

        # Fetch detail
        res = self.client.get(reverse('api:post-detail', args=[self.post_id]))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Facebook-style total: 2 top-level + 3 replies = 5
        self.assertEqual(res.data['comments_count'], 5)
        # Inline cap: first 10 top-level
        self.assertEqual(len(res.data['comments']), 2)
        # The first comment shows replies_count=3 with first 2 replies inline
        c1_in_detail = [c for c in res.data['comments'] if c['id'] == c1.data['id']][0]
        self.assertEqual(c1_in_detail['replies_count'], 3)
        self.assertEqual(len(c1_in_detail['replies']), 2)
