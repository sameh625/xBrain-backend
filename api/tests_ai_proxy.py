"""Tests for Sprint 5: AI Chat proxy.

The Django backend proxies to the standalone FastAPI AI service at
settings.AI_SERVICE_URL. All upstream HTTP is mocked here so the suite never
opens a real socket. We patch the `httpx.Client` constructor inside
`api.views` to return a fake client with a stubbed `.post/.get/.delete/.send`
surface.
"""

from contextlib import contextmanager
from unittest.mock import patch, MagicMock

import httpx
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from .models import ChatSession, User


def _make_user(email, username, phone):
    return User.objects.create_user(
        email=email, username=username, password='TestPass123!',
        first_name='T', last_name='User', phone_number=phone,
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers — fake httpx clients
# ─────────────────────────────────────────────────────────────────────────────


@contextmanager
def _patch_upstream(*, post=None, get=None, delete=None, send=None,
                    post_raises=None, send_raises=None):
    """Patch `httpx.Client` in api.views so any call returns the supplied
    fakes. Either pass a `MagicMock`-style return value, or `*_raises` to make
    the call throw an httpx exception."""

    fake_client = MagicMock()
    if post_raises is not None:
        fake_client.post.side_effect = post_raises
    elif post is not None:
        fake_client.post.return_value = post
    if get is not None:
        fake_client.get.return_value = get
    if delete is not None:
        fake_client.delete.return_value = delete
    if send_raises is not None:
        fake_client.send.side_effect = send_raises
    elif send is not None:
        fake_client.send.return_value = send
    fake_client.build_request.return_value = MagicMock()  # opaque

    fake_client.__enter__ = MagicMock(return_value=fake_client)
    fake_client.__exit__ = MagicMock(return_value=False)

    with patch('api.views.httpx.Client', return_value=fake_client) as cm:
        yield fake_client, cm


def _fake_response(status_code=200, json_body=None, text=None, headers=None):
    """A MagicMock that mimics enough of httpx.Response for our views."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_body if json_body is not None else {}
    resp.text = text if text is not None else ''
    resp.headers = headers or {}
    return resp


def _fake_streaming_response(chunks, status_code=200):
    """A MagicMock mimicking httpx.Response opened with stream=True."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.iter_raw.return_value = iter(chunks)
    resp.close = MagicMock()
    return resp


# ═════════════════════════════════════════════════════════════════════════════
#  ChatSession list + create
# ═════════════════════════════════════════════════════════════════════════════


class ChatListCreateTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.alice = _make_user('alice@e.com', 'aliceuser', '+1000000201')
        self.bob = _make_user('bob@e.com', 'bobuser01', '+1000000202')

    def test_create_chat_requires_auth(self):
        res = self.client.post(reverse('api:ai-chats'), {}, format='json')
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_chat_empty_body_succeeds(self):
        self.client.force_authenticate(user=self.alice)
        res = self.client.post(reverse('api:ai-chats'), {}, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertIn('id', res.data)
        self.assertEqual(res.data['title'], '')
        self.assertTrue(ChatSession.objects.filter(user=self.alice).exists())

    def test_create_chat_with_title(self):
        self.client.force_authenticate(user=self.alice)
        res = self.client.post(
            reverse('api:ai-chats'),
            {'title': 'My algorithms chat'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['title'], 'My algorithms chat')

    def test_list_only_my_chats(self):
        ChatSession.objects.create(user=self.alice, title='alice 1')
        ChatSession.objects.create(user=self.alice, title='alice 2')
        ChatSession.objects.create(user=self.bob, title='bob 1')

        self.client.force_authenticate(user=self.alice)
        res = self.client.get(reverse('api:ai-chats'))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['count'], 2)
        titles = {r['title'] for r in res.data['results']}
        self.assertEqual(titles, {'alice 1', 'alice 2'})


# ═════════════════════════════════════════════════════════════════════════════
#  ChatSession detail (GET history pass-through, PATCH rename, DELETE)
# ═════════════════════════════════════════════════════════════════════════════


class ChatDetailTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.alice = _make_user('alice@e.com', 'aliceuser', '+1000000301')
        self.bob = _make_user('bob@e.com', 'bobuser01', '+1000000302')
        self.chat = ChatSession.objects.create(user=self.alice, title='hi')

    # ─── GET ────────────────────────────────────────────────────────────────

    def test_get_other_users_chat_is_404_not_403(self):
        self.client.force_authenticate(user=self.bob)
        res = self.client.get(reverse('api:ai-chat-detail', kwargs={'pk': self.chat.id}))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_includes_ai_history_when_upstream_ok(self):
        upstream = _fake_response(
            status_code=200,
            json_body={'messages': [{'role': 'user', 'content': 'hi'}]},
        )
        self.client.force_authenticate(user=self.alice)
        with _patch_upstream(get=upstream):
            res = self.client.get(reverse('api:ai-chat-detail', kwargs={'pk': self.chat.id}))
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.assertEqual(res.data['title'], 'hi')
        self.assertEqual(res.data['history'], {'messages': [{'role': 'user', 'content': 'hi'}]})

    def test_get_returns_chat_row_when_ai_unreachable(self):
        self.client.force_authenticate(user=self.alice)
        with _patch_upstream(get=None) as (fake, _):
            fake.get.side_effect = httpx.ConnectError('no route')
            res = self.client.get(reverse('api:ai-chat-detail', kwargs={'pk': self.chat.id}))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIsNone(res.data['history'])
        self.assertIn('history_error', res.data)

    def test_get_treats_upstream_404_as_empty_history(self):
        upstream = _fake_response(status_code=404)
        self.client.force_authenticate(user=self.alice)
        with _patch_upstream(get=upstream):
            res = self.client.get(reverse('api:ai-chat-detail', kwargs={'pk': self.chat.id}))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIsNone(res.data['history'])
        self.assertNotIn('history_error', res.data)

    # ─── PATCH (rename) ─────────────────────────────────────────────────────

    def test_rename_chat(self):
        self.client.force_authenticate(user=self.alice)
        res = self.client.patch(
            reverse('api:ai-chat-detail', kwargs={'pk': self.chat.id}),
            {'title': 'algorithms 101'},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.assertEqual(res.data['title'], 'algorithms 101')
        self.chat.refresh_from_db()
        self.assertEqual(self.chat.title, 'algorithms 101')

    def test_rename_blank_title_is_400(self):
        self.client.force_authenticate(user=self.alice)
        res = self.client.patch(
            reverse('api:ai-chat-detail', kwargs={'pk': self.chat.id}),
            {'title': '   '},
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rename_other_users_chat_is_404(self):
        self.client.force_authenticate(user=self.bob)
        res = self.client.patch(
            reverse('api:ai-chat-detail', kwargs={'pk': self.chat.id}),
            {'title': 'pwned'}, format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    # ─── DELETE ─────────────────────────────────────────────────────────────

    def test_delete_chat_calls_upstream_and_removes_row(self):
        self.client.force_authenticate(user=self.alice)
        with _patch_upstream(delete=_fake_response(status_code=204)) as (fake, _):
            res = self.client.delete(
                reverse('api:ai-chat-detail', kwargs={'pk': self.chat.id}),
            )
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ChatSession.objects.filter(pk=self.chat.id).exists())
        fake.delete.assert_called_once()

    def test_delete_succeeds_even_if_upstream_fails(self):
        self.client.force_authenticate(user=self.alice)
        with _patch_upstream(delete=None) as (fake, _):
            fake.delete.side_effect = httpx.ConnectError('no route')
            res = self.client.delete(
                reverse('api:ai-chat-detail', kwargs={'pk': self.chat.id}),
            )
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ChatSession.objects.filter(pk=self.chat.id).exists())

    def test_delete_other_users_chat_is_404(self):
        self.client.force_authenticate(user=self.bob)
        res = self.client.delete(
            reverse('api:ai-chat-detail', kwargs={'pk': self.chat.id}),
        )
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(ChatSession.objects.filter(pk=self.chat.id).exists())


# ═════════════════════════════════════════════════════════════════════════════
#  AI Ask — streaming pass-through + error mapping + auto-title
# ═════════════════════════════════════════════════════════════════════════════


class AIAskTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.alice = _make_user('alice@e.com', 'aliceuser', '+1000000401')
        self.bob = _make_user('bob@e.com', 'bobuser01', '+1000000402')
        self.chat = ChatSession.objects.create(user=self.alice)

    def _ask(self, body):
        return self.client.post(
            reverse('api:ai-chat-ask', kwargs={'pk': self.chat.id}),
            body, format='json',
        )

    def test_ask_requires_auth(self):
        res = self._ask({'question': 'hi'})
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_ask_other_users_chat_is_404(self):
        self.client.force_authenticate(user=self.bob)
        res = self._ask({'question': 'hi'})
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_ask_streams_chunks_through_and_sets_session_header(self):
        upstream = _fake_streaming_response(
            chunks=[b'hello ', b'world\n', b'__ANSWER_DONE__\n'],
            status_code=200,
        )
        self.client.force_authenticate(user=self.alice)
        with _patch_upstream(send=upstream):
            res = self._ask({'question': 'explain recursion', 'stream': True})
            # StreamingHttpResponse is lazy — drain it BEFORE the patch exits.
            body = b''.join(res.streaming_content)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(body, b'hello world\n__ANSWER_DONE__\n')
        self.assertEqual(res['X-Session-Id'], str(self.chat.id))

    def test_ask_auto_titles_chat_on_first_message(self):
        upstream = _fake_streaming_response(chunks=[b'reply\n'])
        self.client.force_authenticate(user=self.alice)
        with _patch_upstream(send=upstream):
            res = self._ask({'question': 'What is dynamic programming?'})
            b''.join(res.streaming_content)
        self.chat.refresh_from_db()
        self.assertEqual(self.chat.title, 'What is dynamic programming?')

    def test_ask_does_not_overwrite_existing_title(self):
        self.chat.title = 'My existing title'
        self.chat.save()
        upstream = _fake_streaming_response(chunks=[b'reply\n'])
        self.client.force_authenticate(user=self.alice)
        with _patch_upstream(send=upstream):
            res = self._ask({'question': 'a new question'})
            b''.join(res.streaming_content)
        self.chat.refresh_from_db()
        self.assertEqual(self.chat.title, 'My existing title')

    def test_ask_long_question_is_trimmed_for_title(self):
        upstream = _fake_streaming_response(chunks=[b'ok'])
        self.client.force_authenticate(user=self.alice)
        long_q = 'x' * 200
        with _patch_upstream(send=upstream):
            res = self._ask({'question': long_q})
            b''.join(res.streaming_content)
        self.chat.refresh_from_db()
        self.assertEqual(len(self.chat.title), 60)

    # ── Non-streaming path ───────────────────────────────────────────────

    def test_ask_non_streaming_returns_upstream_body(self):
        upstream = _fake_response(
            status_code=200,
            text='{"answer":"recursion is..."}',
            headers={'content-type': 'application/json'},
        )
        self.client.force_authenticate(user=self.alice)
        with _patch_upstream(post=upstream):
            res = self._ask({'question': 'recursion?', 'stream': False})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(b'recursion is', res.content)
        self.assertEqual(res['X-Session-Id'], str(self.chat.id))

    def test_ask_non_streaming_504_on_timeout(self):
        self.client.force_authenticate(user=self.alice)
        with _patch_upstream(post_raises=httpx.TimeoutException('slow')):
            res = self._ask({'question': 'q', 'stream': False})
        self.assertEqual(res.status_code, status.HTTP_504_GATEWAY_TIMEOUT)

    def test_ask_non_streaming_502_on_upstream_error(self):
        self.client.force_authenticate(user=self.alice)
        with _patch_upstream(post_raises=httpx.ConnectError('no route')):
            res = self._ask({'question': 'q', 'stream': False})
        self.assertEqual(res.status_code, status.HTTP_502_BAD_GATEWAY)

    def test_ask_non_streaming_502_on_upstream_5xx(self):
        upstream = _fake_response(status_code=503, text='service down')
        self.client.force_authenticate(user=self.alice)
        with _patch_upstream(post=upstream):
            res = self._ask({'question': 'q', 'stream': False})
        self.assertEqual(res.status_code, status.HTTP_502_BAD_GATEWAY)

    # ── Validation ───────────────────────────────────────────────────────

    def test_ask_empty_question_is_400(self):
        self.client.force_authenticate(user=self.alice)
        res = self._ask({'question': ''})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_ask_too_long_question_is_400(self):
        self.client.force_authenticate(user=self.alice)
        res = self._ask({'question': 'x' * 5000})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
