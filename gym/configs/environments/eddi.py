from typing import Self
from pydantic import Field, model_validator

from red_teaming.gym.enums import Profile
from red_teaming.gym.base import BaseConfig
from red_teaming.gym.configs.servers.eddi import EddiServerConfig
from red_teaming.gym.configs.components.agent import AgentConfig
from red_teaming.gym.configs.components.group import GroupConfig
from red_teaming.gym.configs.components.secret import SecretConfig


class EddiEnvironmentConfig(BaseConfig):
    profile: Profile = Profile.WEAK
    server: EddiServerConfig = Field(default_factory=EddiServerConfig)
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
