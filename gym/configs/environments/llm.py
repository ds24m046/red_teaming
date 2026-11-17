from pydantic import Field

from red_teaming.gym.base import BaseConfig
from red_teaming.gym.configs.servers.llm import LLMServerConfig


class LLMEnvironmentConfig(BaseConfig):
    system_prompt: str = ""
    server: LLMServerConfig = Field(default_factory=LLMServerConfig)
