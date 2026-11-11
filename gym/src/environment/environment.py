import os
from typing import Self, Any
from dotenv import load_dotenv

from red_teaming.gym.src.server.server import EddiServer
from red_teaming.gym.src.session.session import AgentChatSession, GroupChatSession
from red_teaming.gym.src.environment.config import AgentConfig, GroupConfig, GymConfig, SecretConfig
from red_teaming.gym.src.session.utils import id_from_location


class GymEnvironment:
    
    def __init__(self, config: GymConfig, server: EddiServer):
        
        self._config = config
        self._server = server
        
        self._agent_ids = {}
        self._group_ids = {}
        self._sessions = []
    
    @classmethod
    def create(cls, dotenv_path: str, config: GymConfig, server: EddiServer) -> Self:
        
        load_dotenv(dotenv_path)
        
        env = cls(config, server)
        server.start()
        
        try:
            for secret in config.secrets:
                env._store_secret(secret)
            for agent in config.agents:
                env._agent_ids[agent.name] = env._create_agent(agent)
            for group in config.groups:
                env._group_ids[group.name] = env._create_group(group)
        
        except Exception:
            server.destroy()
            raise
        
        return env

    def _store_secret(self, secret: SecretConfig) -> None:
        
        if secret.allowed_agents != ["*"]:
            raise NotImplementedError("per-agent secret grants are not supported yet")
        
        payload = {
            "value": secret.value,
            "description": secret.description,
            "allowedAgents": secret.allowed_agents,
            "allowedHosts": secret.allowed_hosts,
        } 
        
        response = self._server.client.put(f"/secretstore/secrets/default/{secret.name}", json=payload)

        if response.status_code == 503:
            raise RuntimeError("EDDI vault is disabled: set EDDI_VAULT_MASTER_KEY in .env")

        response.raise_for_status()

    def _create_agent(self, agent: AgentConfig) -> str:
        
        if agent.protections.model_dump(exclude_defaults=True) or agent.tools.a2a_peers or agent.a2a_enabled:
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
        
        api_key = os.environ.get(agent.llm.api_key_env, None)
        base_url = os.environ.get(agent.llm.base_url_env, None)
        
        if not api_key:
            raise RuntimeError(f"environment variable {agent.llm.api_key_env} is not set (check .env)")
        
        if not base_url:
            raise RuntimeError(f"environment variable {agent.llm.base_url_env} is not set (check .env)")
        
        body["apiKey"] = api_key
        body["baseUrl"] = base_url
        
        response = self._server.client.post("/administration/agents/setup", json=body)
        
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
        
        response = self._server.client.post("/groupstore/groups", json=body)
        response.raise_for_status()
        
        return id_from_location(response)

    def chat(self, target: str) -> AgentChatSession | GroupChatSession:
        
        client = self._server.client
        
        if target in self._agent_ids:
            session = AgentChatSession(client, self._agent_ids[target])
        elif target in self._group_ids:
            session = GroupChatSession(client, self._group_ids[target])
        else:
            raise KeyError(f"unknown chat target {target!r}")
        
        self._sessions.append(session)
        
        return session

    def close(self) -> None:
        
        for session in self._sessions:
        
            try:
                session.close()
            except Exception:
                pass
        
        self._server.destroy()
