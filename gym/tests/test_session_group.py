import json
import unittest
from unittest.mock import MagicMock

from red_teaming.gym.src.session.session import GroupChatSession
from red_teaming.gym.src.session.models import ChatReply, ChatRequest


class TestGroupChatSession(unittest.TestCase):

    def setUp(self):
        
        self.client = MagicMock()
        self.session = GroupChatSession(
            client=self.client,
            group_id="group-123",
        )

    def test_initialization(self):
        
        self.assertIs(self.session._client, self.client)
        self.assertEqual(self.session._group_id, "group-123")

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
        
        response = MagicMock()
        response.content = b"{}"
        response.json.return_value = {"status": "completed"}
        self.client.post.return_value = response

        reply = self.session.send(
            ChatRequest(message="Check refund", context={})
        )

        self.assertEqual(
            reply.text,
            json.dumps({"status": "completed"}),
        )

    def test_send_empty_response(self):
        
        response = MagicMock()
        response.content = b""
        self.client.post.return_value = response

        reply = self.session.send(
            ChatRequest(message="Hello", context={})
        )

        self.assertEqual(reply.text, "{}")
        self.assertIsNone(reply.conversation_id)

    def test_send_raises_on_http_error(self):
        
        response = MagicMock()
        response.raise_for_status.side_effect = RuntimeError("HTTP error")
        self.client.post.return_value = response

        with self.assertRaises(RuntimeError):
            self.session.send(
                ChatRequest(message="Hello", context={})
            )

    def test_close(self):
    
        self.session.close()

        self.client.post.assert_not_called()


if __name__ == "__main__":
    unittest.main()