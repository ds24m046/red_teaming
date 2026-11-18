import unittest
from unittest.mock import MagicMock, patch

from red_teaming.gym.enums import DiscussionStyle
from red_teaming.gym.configs.models.environments.eddi import EddiEnvironmentConfig
from red_teaming.gym.configs.models.components.agent import AgentConfig, LLMConfig, ProtectionsConfig
from red_teaming.gym.configs.models.components.group import GroupConfig, GroupMemberConfig
from red_teaming.gym.configs.models.components.secret import SecretConfig
from red_teaming.gym.src.environments.eddi import EddiEnvironment


MODULE = "red_teaming.gym.src.environments.eddi"

class TestEddiEnvironment(unittest.TestCase):

    def setUp(self):
        self.agent = AgentConfig(
            name="agent-a",
            system_prompt="Test agent",
            llm=LLMConfig(model="gpt-5-mini"),
        )

        self.agent_b = AgentConfig(
            name="agent-b",
            system_prompt="Test agent B",
            llm=LLMConfig(model="gpt-5-mini"),
        )

        self.group = GroupConfig(
            name="group-a",
            style=next(iter(DiscussionStyle)),
            members=[
                GroupMemberConfig(agent="agent-a"),
                GroupMemberConfig(agent="agent-b"),
            ],
            moderator="agent-a",
            max_rounds=3,
            max_turns=5,
            max_cost_per_discussion=1.0,
        )

        self.secret = SecretConfig(
            name="secret-a",
            value="fake-secret",
        )

        self.config = EddiEnvironmentConfig(
            agents=[self.agent, self.agent_b],
            groups=[self.group],
            secrets=[self.secret],
        )

        self.env = EddiEnvironment(self.config)

    def test_initialization(self):
        self.assertIs(self.env.config, self.config)
        self.assertIsNone(self.env.server)
        self.assertEqual(self.env._agent_ids, {})
        self.assertEqual(self.env._group_ids, {})
        self.assertEqual(self.env._sessions, [])

    @patch(f"{MODULE}.EddiServer")
    @patch.object(EddiEnvironment, "_store_secret")
    @patch.object(EddiEnvironment, "_create_agent", side_effect=["agent-id", "agent-id-b"])
    @patch.object(EddiEnvironment, "_create_group", return_value="group-id")
    def test_create(self, create_group, create_agent, store_secret, server_class):
        server = server_class.return_value

        result = self.env.create()

        self.assertIs(result, self.env)
        server_class.assert_called_once_with(self.config.server)
        server.start.assert_called_once()

        store_secret.assert_called_once_with(self.secret)
        create_agent.assert_any_call(self.agent)
        create_agent.assert_any_call(self.agent_b)
        create_group.assert_called_once_with(self.group)

        self.assertEqual(
            self.env._agent_ids,
            {"agent-a": "agent-id", "agent-b": "agent-id-b"},
        )
        self.assertEqual(self.env._group_ids, {"group-a": "group-id"})

    @patch(f"{MODULE}.EddiServer")
    @patch.object(EddiEnvironment, "_store_secret", side_effect=RuntimeError("Failed"))
    def test_create_destroys_server_on_failure(self, store_secret, server_class):
        server = server_class.return_value

        with self.assertRaisesRegex(RuntimeError, "Failed"):
            self.env.create()

        server.destroy.assert_called_once()
        self.assertIsNone(self.env.server)
        self.assertIsNone(self.env._id)
        self.assertEqual(self.env._agent_ids, {})
        self.assertEqual(self.env._group_ids, {})

    @patch(f"{MODULE}.EddiServer")
    def test_store_secret(self, server_class):
        self.env.server = server_class.return_value
        response = self.env.server.client.put.return_value
        response.status_code = 200

        self.env._store_secret(self.secret)

        self.env.server.client.put.assert_called_once()
        response.raise_for_status.assert_called_once()

    def test_store_secret_rejects_custom_agent_grants(self):
        secret = SecretConfig(
            name="secret",
            value="value",
            allowed_agents=["agent-a"],
        )

        with self.assertRaises(NotImplementedError):
            self.env._store_secret(secret)

    @patch(f"{MODULE}.EddiServer")
    def test_store_secret_vault_disabled(self, server_class):
        self.env.server = server_class.return_value
        self.env.server.client.put.return_value.status_code = 503

        with self.assertRaisesRegex(RuntimeError, "vault is disabled"):
            self.env._store_secret(self.secret)

    @patch.dict(
        "os.environ",
        {
            "OPENAI_API_KEY": "test-key",
            "OPENAI_BASE_URL": "https://example.com",
        },
    )
    @patch(f"{MODULE}.EddiServer")
    @patch(f"{MODULE}.id_from_location", return_value="agent-id")
    def test_create_agent(self, mock_id, server_class):
        self.env.server = server_class.return_value
        response = self.env.server.client.post.return_value
        response.is_error = False
        response.headers = {"Location": "/agents/agent-id"}

        result = self.env._create_agent(self.agent)

        self.assertEqual(result, "agent-id")
        self.env.server.client.post.assert_called_once()
        mock_id.assert_called_once_with(response)

    def test_create_agent_rejects_unsupported_protections(self):
        agent = self.agent.model_copy(
            update={"protections": ProtectionsConfig(input_guardrails=["test"])}
        )

        with self.assertRaises(NotImplementedError):
            self.env._create_agent(agent)

    def test_create_agent_requires_api_key(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(KeyError, "OPENAI_API_KEY"):
                self.env._create_agent(self.agent)

    @patch(f"{MODULE}.EddiServer")
    @patch(f"{MODULE}.id_from_location", return_value="group-id")
    def test_create_group(self, mock_id, server_class):
        self.env.server = server_class.return_value
        self.env._agent_ids = {
            "agent-a": "agent-id",
            "agent-b": "agent-id-b",
        }

        result = self.env._create_group(self.group)

        self.assertEqual(result, "group-id")
        self.env.server.client.post.assert_called_once()
        mock_id.assert_called_once_with(
            self.env.server.client.post.return_value
        )

    def test_get_members(self):
        self.env._agent_ids = {
            "agent-a": "agent-id",
            "agent-b": "agent-id-b",
        }

        members = self.env._get_members(self.group)

        self.assertEqual(
            members,
            [
                {
                    "agentId": "agent-id",
                    "displayName": "agent-a",
                    "speakingOrder": 0,
                },
                {
                    "agentId": "agent-id-b",
                    "displayName": "agent-b",
                    "speakingOrder": 0,
                },
            ],
        )

    def test_get_protocol(self):
        protocol = self.env._get_protocol(self.group)

        self.assertEqual(
            protocol,
            {
                "maxTurns": 5,
                "maxCostPerDiscussion": 1.0,
            },
        )

    def test_get_protocol_without_optional_limits(self):
        group = GroupConfig(
            name="group-a",
            style=next(iter(DiscussionStyle)),
            members=[GroupMemberConfig(agent="agent-a")],
        )

        self.assertEqual(self.env._get_protocol(group), {})

    @patch(f"{MODULE}.EddiServer")
    @patch(f"{MODULE}.AgentSession")
    def test_chat_agent(self, session_class, server_class):
        self.env.server = server_class.return_value
        self.env._agent_ids = {"agent-a": "agent-id"}

        session = self.env.chat("agent-a")

        session_class.assert_called_once_with(
            self.env.server.client,
            "agent-id",
        )
        self.assertIn(session, self.env._sessions)

    @patch(f"{MODULE}.EddiServer")
    @patch(f"{MODULE}.GroupSession")
    def test_chat_group(self, session_class, server_class):
        self.env.server = server_class.return_value
        self.env._group_ids = {"group-a": "group-id"}

        session = self.env.chat("group-a")

        session_class.assert_called_once_with(
            self.env.server.client,
            "group-id",
        )
        self.assertIn(session, self.env._sessions)

    def test_chat_unknown_target(self):
        
        self.env.server = MagicMock()
        
        with self.assertRaises(KeyError):
            self.env.chat("unknown")

    def test_chat_before_create(self):
        with self.assertRaisesRegex(RuntimeError, "not been created"):
            self.env.chat("agent-a")

    @patch(f"{MODULE}.EddiServer")
    def test_close(self, server_class):
        self.env.server = server_class.return_value
        session = MagicMock()
        self.env._sessions = [session]
        self.env._agent_ids = {"agent-a": "agent-id"}
        self.env._group_ids = {"group-a": "group-id"}

        self.env.close()

        session.close.assert_called_once()
        self.env.server
        server_class.return_value.destroy.assert_called_once()
        self.assertIsNone(self.env.server)
        self.assertEqual(self.env._sessions, [])
        self.assertEqual(self.env._agent_ids, {})
        self.assertEqual(self.env._group_ids, {})

    @patch(f"{MODULE}.EddiServer")
    def test_close_continues_after_session_error(self, server_class):
        self.env.server = server_class.return_value

        session_a = MagicMock()
        session_a.close.side_effect = RuntimeError("Failed")
        session_b = MagicMock()

        self.env._sessions = [session_a, session_b]

        self.env.close()

        session_a.close.assert_called_once()
        session_b.close.assert_called_once()
        server_class.return_value.destroy.assert_called_once()


if __name__ == "__main__":
    unittest.main()
