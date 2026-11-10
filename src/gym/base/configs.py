from pathlib import Path

from typing import Self
from pydantic import BaseModel, ConfigDict, Field, model_validator

from red_teaming.src.gym.base.enums import DiscussionStyle, Profile


class ConfigModel(BaseModel):
    """Base for all config objects: unknown JSON keys are rejected."""

    model_config = ConfigDict(extra="forbid")


class LLMConfig(ConfigModel):
    """LLM behind an agent."""

    provider: str = "openai-compatible"
    model: str
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    api_key_env: str = "HF_TOKEN"
    base_url_env: str = "HF_BASE_URL"

class A2APeerConfig(ConfigModel):
    """Remote agent reachable over A2A."""

    name: str
    url: str
    api_key: str | None = None
    timeout_ms: int = Field(default=30_000, gt=0)


class ToolsConfig(ConfigModel):
    """Tools an agent may call."""

    builtin: list[str] = Field(default_factory=list)
    mcp_server_urls: list[str] = Field(default_factory=list)
    openapi_spec_url: str | None = None
    a2a_peers: list[A2APeerConfig] = Field(default_factory=list)


class ProtectionsConfig(ConfigModel):
    """Per-agent defenses; all off by default (weak profile)."""

    input_guardrails: list[str] = Field(default_factory=list)
    output_guardrails: list[str] = Field(default_factory=list)
    tool_call_guardrails: list[str] = Field(default_factory=list)
    approval_required_tools: list[str] = Field(default_factory=list)


class AgentConfig(ConfigModel):
    """One EDDI agent."""

    name: str = Field(min_length=1)
    role: str = ""
    system_prompt: str
    llm: LLMConfig
    tools: ToolsConfig = Field(default_factory=ToolsConfig)
    protections: ProtectionsConfig = Field(default_factory=ProtectionsConfig)
    canary: str | None = None
    a2a_enabled: bool = False


class GroupMemberConfig(ConfigModel):
    agent: str
    display_name: str | None = None
    speaking_order: int = Field(default=0, ge=0)


class GroupConfig(ConfigModel):
    """One EDDI group (a collaboration of existing agents)."""

    name: str = Field(min_length=1)
    style: DiscussionStyle
    members: list[GroupMemberConfig] = Field(min_length=1)
    moderator: str | None = None
    max_rounds: int = Field(default=3, gt=0)
    max_turns: int | None = Field(default=None, gt=0)
    max_cost_per_discussion: float | None = Field(default=None, gt=0)


class ServerConfig(ConfigModel):
    """How to reach the local EDDI server."""

    url: str = "http://localhost:7070"
    startup_timeout_s: int = Field(default=120, gt=0)
    request_timeout_s: int = Field(default=60, gt=0)
    auth_token: str | None = None
    compose_file: Path | None = None
    compose_project: str = "skybook-gym"


class SecretConfig(ConfigModel):
    """Fake secret stored in EDDI's vault; tools reference it as ${vault:name}. Attack surface."""

    name: str = Field(min_length=1)
    value: str = Field(min_length=1)
    description: str = ""
    allowed_agents: list[str] = Field(default_factory=lambda: ["*"])
    allowed_hosts: list[str] = Field(default_factory=lambda: ["*"])


class GymConfig(ConfigModel):
    """Whole gym definition, loaded from gym_config.json."""

    name: str
    description: str = ""
    profile: Profile = Profile.WEAK
    server: ServerConfig = Field(default_factory=ServerConfig)
    secrets: list[SecretConfig] = Field(default_factory=list)
    agents: list[AgentConfig] = Field(min_length=1)
    groups: list[GroupConfig] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_references(self) -> Self:
        
        agent_names = [a.name for a in self.agents]
        
        if len(set(agent_names)) != len(agent_names):
            raise ValueError("agent names must be unique")
        
        group_names = [g.name for g in self.groups]
        
        if len(set(group_names)) != len(group_names):
            raise ValueError("group names must be unique")
        
        if set(agent_names) & set(group_names):
            raise ValueError("agent and group names must not overlap (chat targets)")
        
        known = set(agent_names)
        
        for group in self.groups:
        
            refs = [m.agent for m in group.members]
        
            if group.moderator:
                refs.append(group.moderator)
        
            missing = set(refs) - known
        
            if missing:
                raise ValueError(f"group {group.name!r} references unknown agents: {sorted(missing)}")
        
        return self

    @classmethod
    def from_json(cls, path: Path) -> Self:
        
        path = Path(path)
        
        config = cls.model_validate_json(path.read_text())
        compose = config.server.compose_file
        
        if compose is not None and not compose.is_absolute():
            config.server.compose_file = (path.parent / compose).resolve()
        
        return config
