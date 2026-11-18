import unittest

from pydantic import ValidationError

from red_teaming.gym.configs.models.gym import GymConfig
from red_teaming.gym.configs.models.environments.llm import LLMEnvironmentConfig
from red_teaming.gym.configs.models.environments.eddi import EddiEnvironmentConfig
from red_teaming.gym.enums import EnvironmentType


class TestGymConfig(unittest.TestCase):

    def test_load_llm_config(self):
        data = {
            "name": "LLM test",
            "description": "Test LLM environment",
            "environment": "llm",
            "config": {
                "system_prompt": "You are a helpful assistant.",
                "server": {
                    "openai_api_key": "OPENAI_API_KEY",
                    "openai_base_url": "OPENAI_BASE_URL",
                    "openai_deployment": "gpt-5-mini",
                    "openai_version": "2025-01-01",
                },
            },
        }

        config = GymConfig.model_validate(data)

        self.assertEqual(config.environment, EnvironmentType.LLM)
        self.assertIsInstance(config.config, LLMEnvironmentConfig)
        self.assertEqual(config.config.system_prompt, "You are a helpful assistant.")
        self.assertEqual(config.config.server.openai_deployment, "gpt-5-mini")

    def test_load_eddi_config(self):
        data = {
            "name": "EDDI test",
            "description": "Test EDDI environment",
            "environment": "eddi",
            "config": {
                "profile": "weak",
                "server": {
                    "url": "http://localhost:7070",
                    "startup_timeout_s": 120,
                    "request_timeout_s": 60,
                    "compose_project": "gym-test",
                },
                "secrets": [
                    {
                        "name": "test-token",
                        "value": "FAKE-TOKEN-123",
                        "description": "Test API token",
                        "allowed_agents": ["*"],
                        "allowed_hosts": ["*"],
                    }
                ],
                "agents": [
                    {
                        "name": "assistant",
                        "role": "General-purpose assistant",
                        "system_prompt": "You are a helpful assistant.",
                        "llm": {
                            "provider": "openai-compatible",
                            "model": "gpt-5-mini",
                            "temperature": 0.0,
                            "openai_api_key": "OPENAI_API_KEY",
                            "openai_base_url": "OPENAI_BASE_URL",
                        },
                        "tools": {
                            "builtin": [],
                            "mcp_server_urls": [],
                        },
                        "protections": {},
                        "canary": "CANARY-TEST-123",
                        "a2a_enabled": False,
                    }
                ],
                "groups": [
                    {
                        "name": "discussion",
                        "style": "PEER_REVIEW",
                        "members": [
                            {
                                "agent": "assistant",
                                "display_name": "Assistant",
                                "speaking_order": 0,
                            }
                        ],
                        "moderator": None,
                        "max_rounds": 3,
                    }
                ],
            },
        }

        config = GymConfig.model_validate(data)

        self.assertEqual(config.environment, EnvironmentType.EDDI)
        self.assertIsInstance(config.config, EddiEnvironmentConfig)
        self.assertEqual(len(config.config.agents), 1)
        self.assertEqual(config.config.agents[0].name, "assistant")
        self.assertEqual(config.config.secrets[0].name, "test-token")
        self.assertEqual(config.config.groups[0].name, "discussion")

    def test_invalid_llm_config_raises_validation_error(self):
        data = {
            "name": "LLM test",
            "description": "Test LLM environment",
            "environment": "llm",
            "config": {
                "server": {
                    "unexpected_field": "invalid",
                },
            },
        }

        with self.assertRaises(ValidationError):
            GymConfig.model_validate(data)

    def test_invalid_eddi_config_raises_validation_error(self):
        data = {
            "name": "EDDI test",
            "description": "Test EDDI environment",
            "environment": "eddi",
            "config": {
                "agents": [],
            },
        }

        with self.assertRaises(ValidationError):
            GymConfig.model_validate(data)

    def test_invalid_environment_raises_validation_error(self):
        data = {
            "name": "Invalid test",
            "description": "Invalid environment",
            "environment": "unknown",
            "config": {},
        }

        with self.assertRaises(ValidationError):
            GymConfig.model_validate(data)

    def test_missing_config_raises_validation_error(self):
        data = {
            "name": "Missing config",
            "description": "Missing nested config",
            "environment": "eddi",
        }

        with self.assertRaises(ValidationError):
            GymConfig.model_validate(data)

    def test_missing_environment_raises_validation_error(self):
        data = {
            "name": "Missing environment",
            "description": "Missing environment field",
            "config": {},
        }

        with self.assertRaises(ValidationError):
            GymConfig.model_validate(data)


if __name__ == "__main__":
    unittest.main()
