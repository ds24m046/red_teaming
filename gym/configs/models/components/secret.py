from pydantic import Field

from red_teaming.gym.base import BaseConfig


class SecretConfig(BaseConfig):
    name: str = Field(min_length=1)
    value: str = Field(min_length=1)
    description: str = ""
    allowed_agents: list[str] = Field(default_factory=lambda: ["*"])
    allowed_hosts: list[str] = Field(default_factory=lambda: ["*"])
