from typing import Self
from pydantic import model_validator

from red_teaming.gym.base import BaseConfig
from red_teaming.gym.enums import EnvironmentType
from red_teaming.gym.configs.environments.llm import LLMEnvironmentConfig
from red_teaming.gym.configs.environments.eddi import EddiEnvironmentConfig


class GymConfig(BaseConfig):
    name: str
    description: str
    environment: EnvironmentType
    config: LLMEnvironmentConfig | EddiEnvironmentConfig
    
    @model_validator(mode="after")
    def validate_environment_config(self) -> Self:
        
        lookup = {
            EnvironmentType.LLM: LLMEnvironmentConfig,
            EnvironmentType.EDDI: EddiEnvironmentConfig,
        }
        
        expected = lookup[self.environment]

        if not isinstance(self.config, expected):
            raise ValueError(f"{self.environment} requires {expected.__name__}")

        return self
