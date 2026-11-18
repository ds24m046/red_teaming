import httpx
import unittest
from unittest.mock import MagicMock
from openai import APIError

from red_teaming.gym.enums import ConversationState
from red_teaming.gym.models import ChatReply, ChatRequest
from red_teaming.gym.src.sessions.llm import LLMSession


class TestLLMSession(unittest.TestCase):

    def setUp(self):
        self.client = MagicMock()
        self.session = LLMSession(
            client=self.client,
            deployment="gpt-5-mini",
            system_prompt="You are a helpful assistant.",
        )

    def mock_response(self, content="Hello!"):
        response = MagicMock()
        response.choices[0].message.content = content
        response.model_dump.return_value = {"choices": []}
        return response

    def test_initialization(self):
        self.assertIs(self.session.client, self.client)
        self.assertEqual(self.session.deployment, "gpt-5-mini")
        self.assertEqual(
            self.session._messages,
            [{"role": "system", "content": "You are a helpful assistant."}],
        )

    def test_send(self):
        self.client.chat.completions.create.return_value = self.mock_response()

        reply = self.session.send(ChatRequest(message="Hi"))

        self.client.chat.completions.create.assert_called_once_with(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hi"},
                {"role": "assistant", "content": "Hello!"},
            ],
        )

        self.assertIsInstance(reply, ChatReply)
        self.assertEqual(reply.text, "Hello!")
        self.assertEqual(reply.state, ConversationState.READY)
        self.assertEqual(reply.raw, {"choices": []})

    def test_send_preserves_conversation_history(self):
        self.client.chat.completions.create.side_effect = [
            self.mock_response("First answer"),
            self.mock_response("Second answer"),
        ]

        self.session.send(ChatRequest(message="First question"))
        self.session.send(ChatRequest(message="Second question"))

        messages = self.client.chat.completions.create.call_args.kwargs["messages"]

        self.assertEqual(
            messages,
            [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "First question"},
                {"role": "assistant", "content": "First answer"},
                {"role": "user", "content": "Second question"},
                {"role": "assistant", "content": "Second answer"},
            ],
        )

    def test_send_with_empty_response(self):
        self.client.chat.completions.create.return_value = self.mock_response(None)

        reply = self.session.send(ChatRequest(message="Hi"))

        self.assertEqual(reply.text, "No response from model")
        self.assertEqual(reply.state, ConversationState.ERROR)
        self.assertEqual(reply.raw, {})

    def test_send_handles_api_error(self):
        error = APIError(
            message="API error",
            request=httpx.Request("POST", "https://example.com"),
            body=None,
        )
        self.client.chat.completions.create.side_effect = error

        reply = self.session.send(ChatRequest(message="Hi"))

        self.assertEqual(reply.text, "API error")
        self.assertEqual(reply.state, ConversationState.ERROR)
        self.assertEqual(reply.raw, {})

    def test_close(self):
        self.session.close()

        self.assertEqual(self.session._messages, [])


if __name__ == "__main__":
    unittest.main()
