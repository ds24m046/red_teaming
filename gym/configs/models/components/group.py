from pydantic import Field
from red_teaming.gym.base import BaseConfig
from red_teaming.gym.enums import DiscussionStyle


class GroupMemberConfig(BaseConfig):
    agent: str
    display_name: str | None = None
    speaking_order: int = Field(default=0, ge=0)


class GroupConfig(BaseConfig):
    name: str = Field(min_length=1)
    style: DiscussionStyle
    members: list[GroupMemberConfig] = Field(min_length=1)
    moderator: str | None = None
    max_rounds: int = Field(default=3, gt=0)
    max_turns: int | None = Field(default=None, gt=0)
    max_cost_per_discussion: float | None = Field(default=None, gt=0)
