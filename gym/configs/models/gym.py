import copy
from typing import Any

from pydantic import model_validator
from red_teaming.gym.base import BaseConfig
from red_teaming.gym.configs.models.environments.eddi import EddiEnvironmentConfig
from red_teaming.gym.configs.models.environments.llm import LLMEnvironmentConfig
from red_teaming.gym.enums import EnvironmentType


class GymConfig(BaseConfig):
    name: str
    description: str
    environment: EnvironmentType
    config: LLMEnvironmentConfig | EddiEnvironmentConfig

    @model_validator(mode="before")
    @classmethod
    def select_environment_config(cls, data: Any) -> Any:

        if not isinstance(data, dict):
            return data

        environment = data.get("environment")
        config = data.get("config")

        if not isinstance(config, dict):
            return data

        data = copy.deepcopy(data)

        if environment == EnvironmentType.LLM or environment == EnvironmentType.LLM.value:
            data["config"] = LLMEnvironmentConfig.model_validate(config)

        elif environment == EnvironmentType.EDDI or environment == EnvironmentType.EDDI.value:
            data["config"] = EddiEnvironmentConfig.model_validate(config)

        return data
