import os
from typing import Self, Any

from dotenv import load_dotenv

from red_teaming.src.gym.base.abstract import ChatSession, EddiServer, GymEnvironment
from red_teaming.src.gym.base.configs import AgentConfig, GroupConfig, GymConfig, SecretConfig
from red_teaming.src.gym.implementations.session import AgentChatSession, GroupChatSession, _id_from_location


class EddiGymEnvironment(GymEnvironment):
    
    def __init__(self, config: GymConfig, server: EddiServer):
        
        self._config = config
        self._server = server
        
        self._agent_ids: dict[str, str] = {}
        self._group_ids: dict[str, str] = {}
        self._sessions: list[ChatSession] = []

    @classmethod
    def create(cls, config: GymConfig, server: EddiServer) -> Self:
        
        load_dotenv()
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
            "builtInToolsWhitelist": agent.tools.builtin,
            "mcpServerUrls": agent.tools.mcp_server_urls,
            "deploy": True,
            "environment": "production",
        }
        
        api_key = os.environ.get(agent.llm.api_key_env)
        
        if not api_key:
            raise RuntimeError(f"environment variable {agent.llm.api_key_env} is not set (check .env)")
        
        body["apiKey"] = api_key
        
        response = self._server.client.post("/administration/agents/setup", json=body)
        response.raise_for_status()
        
        if "Location" in response.headers:
            return _id_from_location(response)
        
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
        
        return _id_from_location(response)

    def chat(self, target: str) -> ChatSession:
        
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
