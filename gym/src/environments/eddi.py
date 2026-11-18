import os
import uuid
import logging
from typing import Any

from red_teaming.gym.src.utils import id_from_location
from red_teaming.gym.src.servers.eddi import EddiServer
from red_teaming.gym.src.sessions.agent import AgentSession
from red_teaming.gym.src.sessions.group import GroupSession
from red_teaming.gym.base import BaseEnvironment, BaseSession
from red_teaming.gym.configs.models.environments.eddi import EddiEnvironmentConfig
from red_teaming.gym.configs.models.components.agent import AgentConfig
from red_teaming.gym.configs.models.components.group import GroupConfig
from red_teaming.gym.configs.models.components.secret import SecretConfig


logger = logging.getLogger(__name__)

class EddiEnvironment(BaseEnvironment):

    def __init__(self, config: EddiEnvironmentConfig):
        
        self.config = config
        self.server = None

        self._id = None
        self._agent_ids: dict[str, str] = {}
        self._group_ids: dict[str, str] = {}
        self._sessions: list[BaseSession] = []

    def _store_secret(self, secret: SecretConfig) -> None:

        if secret.allowed_agents != ["*"]:
            raise NotImplementedError("per-agent secret grants are not supported yet")

        payload = {
            "value": secret.value,
            "description": secret.description,
            "allowedAgents": secret.allowed_agents,
            "allowedHosts": secret.allowed_hosts,
        }

        response = self.server.client.put(f"/secretstore/secrets/default/{secret.name}", json=payload)

        if response.status_code == 503:
            raise RuntimeError("EDDI vault is disabled: set EDDI_VAULT_MASTER_KEY in .env")

        response.raise_for_status()

    def _create_agent(self, agent: AgentConfig) -> str:

        if (
            agent.protections.model_dump(exclude_defaults=True)
            or agent.tools.a2a_peers
            or agent.a2a_enabled
        ):
            raise NotImplementedError("protections and A2A are not supported yet")

        if agent.tools.openapi_spec_url:
            raise NotImplementedError("OpenAPI tools are not supported yet")

        body = {
            "agentName": agent.name,
            "systemPrompt": agent.system_prompt,
            "provider": agent.llm.provider,
            "model": agent.llm.model,
            "enableBuiltInTools": bool(agent.tools.builtin),
            "builtInToolsWhitelist": ",".join(agent.tools.builtin),
            "mcpServerUrls": ",".join(agent.tools.mcp_server_urls),
            "deploy": True,
            "environment": "production",
        }

        body["apiKey"] = os.environ[agent.llm.openai_api_key]
        body["baseUrl"] = os.environ[agent.llm.openai_base_url]

        response = self.server.client.post("/administration/agents/setup", json=body)

        if response.is_error:
            raise RuntimeError(f"agent {agent.name!r} setup failed [{response.status_code}]: {response.text}")

        if "Location" in response.headers:
            return id_from_location(response)

        return response.json()["agentId"]

    def _get_members(self, group: GroupConfig) -> list[dict[str, Any]]:

        members = []
        for m in group.members:
            
            member = {
                "agentId": self._agent_ids[m.agent],
                "displayName": m.display_name or m.agent,
                "speakingOrder": m.speaking_order,
            }

            members.append(member)

        return members

    def _get_protocol(self, group: GroupConfig) -> dict[str, Any]:

        protocol = {}

        if group.max_turns is not None:
            protocol["maxTurns"] = group.max_turns

        if group.max_cost_per_discussion is not None:
            protocol["maxCostPerDiscussion"] = group.max_cost_per_discussion

        return protocol

    def _create_group(self, group: GroupConfig) -> str:

        body = {
            "name": group.name,
            "style": group.style.value,
            "members": self._get_members(group),
            "maxRounds": group.max_rounds,
            "protocol": self._get_protocol(group),
        }

        if group.moderator:
            body["moderatorAgentId"] = self._agent_ids[group.moderator]

        response = self.server.client.post("/groupstore/groups", json=body)
        response.raise_for_status()

        return id_from_location(response)
    
    def create(self) -> "EddiEnvironment":
        
        self._id = str(uuid.uuid4())
        self.server = EddiServer(self.config.server)

        try:
            self.server.start()

            for secret in self.config.secrets:
                self._store_secret(secret)

            for agent in self.config.agents:
                self._agent_ids[agent.name] = self._create_agent(agent)

            for group in self.config.groups:
                self._group_ids[group.name] = self._create_group(group)

        except Exception:
            self.server.destroy()
            self.server = None
            
            self._id = None
            self._agent_ids.clear()
            self._group_ids.clear()
            
            raise

        return self

    def chat(self, target: str) -> BaseSession:
        
        if self.server is None:
            raise RuntimeError("Environment has not been created")

        client = self.server.client

        if target in self._agent_ids:
            session = AgentSession(client, self._agent_ids[target])
        elif target in self._group_ids:
            session = GroupSession(client, self._group_ids[target])
        else:
            raise KeyError(f"Unknown chat target: {target!r}")

        self._sessions.append(session)
        
        return session

    def close(self) -> None:
        
        try:
            for session in self._sessions:
                try:
                    session.close()
                except Exception:
                    logger.exception("Failed to close session")
        
        finally:
            
            if self.server is not None:
                self.server.destroy()
                self.server = None

            self._id = None
            self._sessions.clear()
            self._agent_ids.clear()
            self._group_ids.clear()
