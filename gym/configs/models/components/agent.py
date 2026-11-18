from pydantic import Field
from red_teaming.gym.base import BaseConfig


class LLMConfig(BaseConfig):
    provider: str = "openai-compatible"
    model: str
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    openai_api_key: str = "OPENAI_API_KEY"
    openai_base_url: str = "OPENAI_BASE_URL"


class A2APeerConfig(BaseConfig):
    name: str
    url: str
    api_key: str | None = None
    timeout_ms: int = Field(default=30_000, gt=0)


class ToolsConfig(BaseConfig):
    builtin: list[str] = Field(default_factory=list)
    mcp_server_urls: list[str] = Field(default_factory=list)
    openapi_spec_url: str | None = None
    a2a_peers: list[A2APeerConfig] = Field(default_factory=list)


class ProtectionsConfig(BaseConfig):
    input_guardrails: list[str] = Field(default_factory=list)
    output_guardrails: list[str] = Field(default_factory=list)
    tool_call_guardrails: list[str] = Field(default_factory=list)
    approval_required_tools: list[str] = Field(default_factory=list)


class AgentConfig(BaseConfig):
    name: str = Field(min_length=1)
    role: str = ""
    system_prompt: str
    llm: LLMConfig
    tools: ToolsConfig = Field(default_factory=ToolsConfig)
    protections: ProtectionsConfig = Field(default_factory=ProtectionsConfig)
    canary: str | None = None
    a2a_enabled: bool = False
