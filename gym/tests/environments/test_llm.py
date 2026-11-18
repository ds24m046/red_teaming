import unittest
from unittest.mock import MagicMock, patch

from red_teaming.gym.configs.models.environments.llm import LLMEnvironmentConfig
from red_teaming.gym.src.environments.llm import LLMEnvironment


MODULE = "red_teaming.gym.src.environments.llm"

class TestLLMEnvironment(unittest.TestCase):

    def setUp(self):
        self.config = LLMEnvironmentConfig(
            system_prompt="You are a helpful assistant.",
        )
        self.env = LLMEnvironment(self.config)

    def test_initialization(self):
        self.assertIs(self.env.config, self.config)
        self.assertIsNone(self.env.server)
        self.assertIsNone(self.env._id)
        self.assertEqual(self.env._sessions, [])

    @patch(f"{MODULE}.LLMServer")
    def test_create(self, server_class):
        server = server_class.return_value

        result = self.env.create()

        self.assertIs(result, self.env)
        server_class.assert_called_once_with(self.config.server)
        server.start.assert_called_once()

        self.assertIsNotNone(self.env._id)
        self.assertEqual(len(self.env._id), 36)

    @patch(f"{MODULE}.LLMServer")
    def test_create_cleans_up_on_failure(self, server_class):
        server = server_class.return_value
        server.start.side_effect = RuntimeError("Failed to start")

        with self.assertRaisesRegex(RuntimeError, "Failed to start"):
            self.env.create()

        server.destroy.assert_called_once()
        self.assertIsNone(self.env.server)
        self.assertIsNone(self.env._id)

    @patch(f"{MODULE}.LLMSession")
    @patch(f"{MODULE}.LLMServer")
    def test_chat(self, server_class, session_class):
        server = server_class.return_value
        server.deployment = "gpt-5-mini"

        self.env.create()
        target = self.env._id

        session = self.env.chat(target)

        session_class.assert_called_once_with(
            server.client,
            "gpt-5-mini",
            self.config.system_prompt,
        )
        self.assertIn(session, self.env._sessions)

    def test_chat_rejects_unknown_target(self):
        self.env._id = "valid-id"

        with self.assertRaisesRegex(ValueError, "Unknown target"):
            self.env.chat("invalid-id")

    def test_chat_before_create(self):
        with self.assertRaisesRegex(ValueError, "Unknown target"):
            self.env.chat("some-id")

    @patch(f"{MODULE}.LLMServer")
    def test_close(self, server_class):
        server = server_class.return_value
        self.env.server = server
        self.env._id = "test-id"

        session = MagicMock()
        self.env._sessions = [session]

        self.env.close()

        session.close.assert_called_once()
        server.destroy.assert_called_once()

        self.assertIsNone(self.env.server)
        self.assertIsNone(self.env._id)
        self.assertEqual(self.env._sessions, [])

    @patch(f"{MODULE}.LLMServer")
    def test_close_continues_after_session_error(self, server_class):
        server = server_class.return_value
        self.env.server = server

        session_a = MagicMock()
        session_a.close.side_effect = RuntimeError("Failed")
        session_b = MagicMock()

        self.env._sessions = [session_a, session_b]

        self.env.close()

        session_a.close.assert_called_once()
        session_b.close.assert_called_once()
        server.destroy.assert_called_once()


if __name__ == "__main__":
    unittest.main()
