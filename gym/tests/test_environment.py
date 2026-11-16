import unittest
from unittest.mock import MagicMock, patch

from red_teaming.gym.src.environment.environment import GymEnvironment
from red_teaming.gym.src.environment.enums import DiscussionStyle
from red_teaming.gym.src.environment.config import ProtectionsConfig
from red_teaming.gym.src.environment.config import (
    AgentConfig,
    GroupConfig,
    GroupMemberConfig,
    GymConfig,
    LLMConfig,
    SecretConfig,
)


MODULE = "red_teaming.gym.src.environment.environment"

class TestGymEnvironment(unittest.TestCase):

    def setUp(self):
        
        self.server = MagicMock()

        self.agent = AgentConfig(
            name="agent-a",
            system_prompt="Test agent",
            llm=LLMConfig(model="gpt-5-mini"),
        )

        self.group = GroupConfig(
            name="group-a",
            style=next(iter(DiscussionStyle)),
            members=[GroupMemberConfig(agent="agent-a")],
        )

        self.secret = SecretConfig(
            name="secret-a",
            value="fake-secret",
        )

        self.config = GymConfig(
            name="test-gym",
            agents=[self.agent],
            groups=[self.group],
            secrets=[self.secret],
        )

        self.env = GymEnvironment(self.config, self.server)
    
    def test_initialization(self):
    
        self.assertIs(self.env._config, self.config)
        self.assertIs(self.env._server, self.server)
        self.assertEqual(self.env._agent_ids, {})
        self.assertEqual(self.env._group_ids, {})

    @patch(f"{MODULE}.load_dotenv")
    @patch.object(GymEnvironment, "_store_secret")
    @patch.object(GymEnvironment, "_create_agent", return_value="agent-id")
    @patch.object(GymEnvironment, "_create_group", return_value="group-id")
    def test_create(self, create_group, create_agent, store_secret, load_dotenv):
        
        env = GymEnvironment.create(".env", self.config, self.server)

        load_dotenv.assert_called_once_with(".env")
        self.server.start.assert_called_once()
        store_secret.assert_called_once_with(self.secret)
        create_agent.assert_called_once_with(self.agent)
        create_group.assert_called_once_with(self.group)

        self.assertEqual(env._agent_ids, {"agent-a": "agent-id"})
        self.assertEqual(env._group_ids, {"group-a": "group-id"})

    @patch(f"{MODULE}.load_dotenv")
    @patch.object(GymEnvironment, "_store_secret", side_effect=RuntimeError("Failed"))
    def test_create_destroys_server_on_failure(self, *_):
        
        with self.assertRaises(RuntimeError):
            GymEnvironment.create(".env", self.config, self.server)

        self.server.destroy.assert_called_once()

    def test_store_secret(self):
        
        response = MagicMock(status_code=200)
        self.server.client.put.return_value = response

        self.env._store_secret(self.secret)

        self.server.client.put.assert_called_once()
        response.raise_for_status.assert_called_once()

    def test_store_secret_rejects_custom_agent_grants(self):
        
        secret = SecretConfig(
            name="secret",
            value="value",
            allowed_agents=["agent-a"],
        )

        with self.assertRaises(NotImplementedError):
            self.env._store_secret(secret)

    def test_store_secret_vault_disabled(self):
        
        self.server.client.put.return_value.status_code = 503

        with self.assertRaisesRegex(RuntimeError, "vault is disabled"):
            self.env._store_secret(self.secret)

    @patch.dict(
        "os.environ",
        {
            "OPENAI_API_KEY": "test-key",
            "OPENAI_BASE_URL": "https://example.com",
        },
    )
    @patch(f"{MODULE}.id_from_location", return_value="agent-id")
    def test_create_agent(self, mock_id):
        
        response = MagicMock(is_error=False)
        response.headers = {"Location": "/agents/agent-id"}
        self.server.client.post.return_value = response

        result = self.env._create_agent(self.agent)

        self.assertEqual(result, "agent-id")
        self.server.client.post.assert_called_once()
        mock_id.assert_called_once_with(response)
    
    def test_create_agent_rejects_unsupported_protections(self):
        
        agent = self.agent.model_copy(
            update={"protections": ProtectionsConfig(input_guardrails=["test"])}
        )
        
        with self.assertRaises(NotImplementedError):
            self.env._create_agent(agent)
    
    def test_create_agent_requires_api_key(self):
        
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "OPENAI_API_KEY"):
                self.env._create_agent(self.agent)

    @patch(f"{MODULE}.id_from_location", return_value="group-id")
    def test_create_group(self, mock_id):
        
        self.env._agent_ids = {"agent-a": "agent-id"}

        response = MagicMock()
        self.server.client.post.return_value = response

        result = self.env._create_group(self.group)

        self.assertEqual(result, "group-id")
        self.server.client.post.assert_called_once()
        mock_id.assert_called_once_with(response)

    # Chat sessions

    @patch(f"{MODULE}.AgentChatSession")
    def test_chat_agent(self, mock_session):
        
        self.env._agent_ids = {"agent-a": "agent-id"}

        session = self.env.chat("agent-a")

        mock_session.assert_called_once_with(
            self.server.client, "agent-id"
        )
        self.assertIn(session, self.env._sessions)

    @patch(f"{MODULE}.GroupChatSession")
    def test_chat_group(self, mock_session):
        
        self.env._group_ids = {"group-a": "group-id"}

        session = self.env.chat("group-a")

        mock_session.assert_called_once_with(
            self.server.client, "group-id"
        )
        self.assertIn(session, self.env._sessions)

    def test_chat_unknown_target(self):
        with self.assertRaises(KeyError):
            self.env.chat("unknown")
    
    def test_close(self):
    
        session = MagicMock()
        self.env._sessions = [session]

        self.env.close()

        session.close.assert_called_once()
        self.server.destroy.assert_called_once()

    def test_close_continues_after_session_error(self):
    
        session_a = MagicMock()
        session_a.close.side_effect = RuntimeError("Failed")
        session_b = MagicMock()

        self.env._sessions = [session_a, session_b]
        self.env.close()

        session_b.close.assert_called_once()
        self.server.destroy.assert_called_once()


if __name__ == "__main__":
    unittest.main()