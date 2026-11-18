import json
import unittest
from unittest.mock import MagicMock

from red_teaming.gym.enums import ConversationState
from red_teaming.gym.models import ChatReply, ChatRequest
from red_teaming.gym.src.sessions.group import GroupSession


class TestGroupSession(unittest.TestCase):

    def setUp(self):
        self.client = MagicMock()
        self.session = GroupSession(
            client=self.client,
            group_id="group-123",
        )

    def test_initialization(self):
        self.assertIs(self.session._client, self.client)
        self.assertEqual(self.session._group_id, "group-123")
        self.assertFalse(self.session._closed)

    def test_send_decision(self):
        response = MagicMock()
        response.content = b'{"decision": "Approved"}'
        response.json.return_value = {
            "id": "conversation-123",
            "decision": "Approved",
        }
        self.client.post.return_value = response

        reply = self.session.send(
            ChatRequest(message="Check refund", context={})
        )

        self.client.post.assert_called_once_with(
            "/groups/group-123/conversations",
            json={"question": "Check refund"},
        )

        self.assertIsInstance(reply, ChatReply)
        self.assertEqual(reply.text, "Approved")
        self.assertEqual(reply.conversation_id, "conversation-123")
        self.assertEqual(reply.state, ConversationState.READY)

    def test_send_synthesized_answer(self):
        response = MagicMock()
        response.content = b"{}"
        response.json.return_value = {
            "synthesizedAnswer": "Refund approved"
        }
        self.client.post.return_value = response

        reply = self.session.send(
            ChatRequest(message="Check refund", context={})
        )

        self.assertEqual(reply.text, "Refund approved")

    def test_send_falls_back_to_json(self):
        raw = {"status": "completed"}

        response = MagicMock()
        response.content = b"{}"
        response.json.return_value = raw
        self.client.post.return_value = response

        reply = self.session.send(
            ChatRequest(message="Check refund", context={})
        )

        self.assertEqual(reply.text, json.dumps(raw))
        self.assertEqual(reply.raw, raw)

    def test_send_empty_response(self):
        response = MagicMock()
        response.content = b""
        self.client.post.return_value = response

        reply = self.session.send(
            ChatRequest(message="Hello", context={})
        )

        self.assertEqual(reply.text, "{}")
        self.assertEqual(reply.raw, {})
        self.assertIsNone(reply.conversation_id)

    def test_send_raises_on_http_error(self):
        response = MagicMock()
        response.raise_for_status.side_effect = RuntimeError("HTTP error")
        self.client.post.return_value = response

        with self.assertRaises(RuntimeError):
            self.session.send(
                ChatRequest(message="Hello", context={})
            )

    def test_send_after_close_raises(self):
        self.session.close()

        with self.assertRaisesRegex(RuntimeError, "Session is closed"):
            self.session.send(
                ChatRequest(message="Hello", context={})
            )

        self.client.post.assert_not_called()

    def test_close(self):
        self.session.close()

        self.assertTrue(self.session._closed)
        self.client.post.assert_not_called()

    def test_close_is_idempotent(self):
        self.session.close()
        self.session.close()

        self.assertTrue(self.session._closed)
        self.client.post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
