import unittest
from unittest.mock import MagicMock

from red_teaming.gym.src.sessions.agent import AgentSession
from red_teaming.gym.models import ChatReply, ChatRequest, ConversationState


class TestAgentSession(unittest.TestCase):

    def setUp(self):
        self.client = MagicMock()
        self.agent_id = "agent-123"

        response = MagicMock()
        response.headers = {
            "Location": "/agents/agent-123/conversations/conv-456"
        }
        self.client.post.return_value = response

        self.session = AgentSession(
            client=self.client,
            agent_id=self.agent_id,
        )

    def test_initialization(self):
        self.client.post.assert_called_once_with(
            "/agents/agent-123/start",
            params={
                "environment": "production",
                "userId": unittest.mock.ANY,
            },
        )

        self.assertEqual(self.session._conversation_id, "conv-456")

    def test_initialization_with_custom_environment(self):
        self.client.reset_mock()

        AgentSession(
            client=self.client,
            agent_id=self.agent_id,
            env="development",
        )

        self.client.post.assert_called_once_with(
            "/agents/agent-123/start",
            params={
                "environment": "development",
                "userId": unittest.mock.ANY,
            },
        )

    def test_initialization_raises_on_http_error(self):
        self.client.post.return_value.raise_for_status.side_effect = (
            RuntimeError("HTTP error")
        )

        with self.assertRaises(RuntimeError):
            AgentSession(self.client, self.agent_id)

    def test_parse_response(self):
        raw = {
            "conversationOutputs": [
                {"output": [{"text": "Old response"}]},
                {
                    "output": [
                        {"text": "Hello"},
                        {"text": "World"},
                    ]
                },
            ]
        }

        self.assertEqual(
            self.session._parse_response(raw),
            ["Hello", "World"],
        )

    def test_parse_response_ignores_invalid_items(self):
        raw = {
            "conversationOutputs": [
                {
                    "output": [
                        {"text": "Hello"},
                        {"other": "value"},
                        "invalid",
                        {"text": ""},
                        {},
                    ]
                }
            ]
        }

        self.assertEqual(self.session._parse_response(raw), ["Hello"])

    def test_parse_response_without_outputs(self):
        self.assertEqual(self.session._parse_response({}), [])

    def test_send(self):
        response = MagicMock()
        response.content = b'{"conversationState": "READY"}'
        response.json.return_value = {
            "conversationState": "READY",
            "conversationOutputs": [
                {"output": [{"text": "Hello from agent"}]}
            ],
        }
        self.client.post.return_value = response

        request = ChatRequest(
            message="Hello",
            context={"name": "Alice"},
        )

        reply = self.session.send(request)

        self.client.post.assert_called_with(
            "/agents/conv-456",
            json={
                "input": "Hello",
                "context": {
                    "name": {
                        "type": "string",
                        "value": "Alice",
                    }
                },
            },
        )

        self.assertIsInstance(reply, ChatReply)
        self.assertEqual(reply.text, "Hello from agent")
        self.assertEqual(reply.conversation_id, "conv-456")
        self.assertEqual(reply.state, ConversationState.READY)

    def test_send_without_context(self):
        response = MagicMock()
        response.content = b"{}"
        response.json.return_value = {}
        self.client.post.return_value = response

        self.session.send(ChatRequest(message="Hello", context={}))

        self.client.post.assert_called_with(
            "/agents/conv-456",
            json={"input": "Hello", "context": {}},
        )

    def test_send_with_empty_response(self):
        response = MagicMock()
        response.content = b""
        self.client.post.return_value = response

        reply = self.session.send(
            ChatRequest(message="Hello", context={})
        )

        self.assertEqual(reply.text, "")
        self.assertEqual(reply.raw, {})
        self.assertEqual(reply.conversation_id, "conv-456")

    def test_send_raises_on_http_error(self):
        response = MagicMock()
        response.raise_for_status.side_effect = RuntimeError("HTTP error")
        self.client.post.return_value = response

        with self.assertRaises(RuntimeError):
            self.session.send(ChatRequest(message="Hello", context={}))

    def test_send_after_close_raises(self):
        self.session.close()

        with self.assertRaisesRegex(RuntimeError, "Session is closed"):
            self.session.send(ChatRequest(message="Hello", context={}))

    def test_close(self):
        self.session.close()

        self.client.post.assert_called_with(
            "/agents/conv-456/endConversation"
        )
        self.assertIsNone(self.session._conversation_id)

    def test_close_is_idempotent(self):
        self.session.close()
        self.client.reset_mock()

        self.session.close()

        self.client.post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
