import os
import unittest
from unittest.mock import patch, MagicMock

from red_teaming.gym.configs.servers.llm import LLMServerConfig
from red_teaming.gym.src.servers.llm import LLMServer


MODULE = "red_teaming.gym.src.servers.llm"


class TestLLMServer(unittest.TestCase):

    def setUp(self):
        self.env = {
            "OPENAI_API_KEY": "test-api-key",
            "OPENAI_BASE_URL": "https://test.openai.azure.com",
            "OPENAI_DEPLOYMENT": "gpt-5-mini",
            "OPENAI_VERSION": "2025-01-01-preview",
        }

        self.env_patcher = patch.dict(os.environ, self.env)
        self.env_patcher.start()

        self.azure_patcher = patch(f"{MODULE}.AzureOpenAI")
        self.mock_azure = self.azure_patcher.start()

        self.config = LLMServerConfig()
        self.server = LLMServer(self.config)

    def tearDown(self):
        self.azure_patcher.stop()
        self.env_patcher.stop()

    def test_initialization_resolves_environment_variables(self):
        self.assertEqual(self.server._config.openai_api_key, "test-api-key")
        self.assertEqual(
            self.server._config.openai_base_url,
            "https://test.openai.azure.com",
        )
        self.assertEqual(self.server._config.openai_deployment, "gpt-5-mini")
        self.assertEqual(
            self.server._config.openai_version,
            "2025-01-01-preview",
        )
        self.assertIsNone(self.server._client)

    def test_initialization_fails_when_environment_variable_is_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(KeyError):
                LLMServer(self.config)

    def test_client_before_start_raises_error(self):
        with self.assertRaisesRegex(RuntimeError, "not been started"):
            _ = self.server.client

    def test_start_creates_azure_client(self):
        self.server.start()

        self.mock_azure.assert_called_once_with(
            api_version="2025-01-01-preview",
            azure_endpoint="https://test.openai.azure.com",
            api_key="test-api-key",
            max_retries=20,
        )

        self.assertIs(self.server.client, self.mock_azure.return_value)

    def test_destroy_clears_client(self):
        self.server.start()
        self.server.destroy()

        self.assertIsNone(self.server._client)

        with self.assertRaises(RuntimeError):
            _ = self.server.client


if __name__ == "__main__":
    unittest.main()
