import unittest
from pydantic import ValidationError

from red_teaming.gym.enums import DiscussionStyle
from red_teaming.gym.configs.models.environments.eddi import EddiEnvironmentConfig
from red_teaming.gym.configs.models.components.agent import AgentConfig
from red_teaming.gym.configs.models.components.group import GroupConfig
from red_teaming.gym.configs.models.components.group import GroupMemberConfig
from red_teaming.gym.configs.models.components.agent import LLMConfig


class TestEddiEnvironmentConfig(unittest.TestCase):

    def setUp(self):
        self.agent_a = AgentConfig(
            name="agent-a",
            system_prompt="You are agent A.",
            llm=LLMConfig(model="gpt-5-mini"),
        )

        self.agent_b = AgentConfig(
            name="agent-b",
            system_prompt="You are agent B.",
            llm=LLMConfig(model="gpt-5-mini"),
        )

        self.group = GroupConfig(
            name="group-a",
            style=next(iter(DiscussionStyle)),
            members=[
                GroupMemberConfig(agent="agent-a"),
                GroupMemberConfig(agent="agent-b"),
            ],
            moderator="agent-a",
        )

    def test_valid_references(self):
        config = EddiEnvironmentConfig(
            agents=[self.agent_a, self.agent_b],
            groups=[self.group],
        )

        self.assertEqual(len(config.agents), 2)
        self.assertEqual(len(config.groups), 1)

    def test_duplicate_agent_names(self):
        duplicate = self.agent_a.model_copy()

        with self.assertRaisesRegex(ValidationError, "agent names must be unique"):
            EddiEnvironmentConfig(
                agents=[self.agent_a, duplicate],
            )

    def test_duplicate_group_names(self):
        duplicate = self.group.model_copy()

        with self.assertRaisesRegex(ValidationError, "group names must be unique"):
            EddiEnvironmentConfig(
                agents=[self.agent_a],
                groups=[self.group, duplicate],
            )

    def test_agent_and_group_names_must_not_overlap(self):
        group = GroupConfig(
            name="agent-a",
            style=next(iter(DiscussionStyle)),
            members=[GroupMemberConfig(agent="agent-a")],
        )

        with self.assertRaisesRegex(
            ValidationError,
            "agent and group names must not overlap",
        ):
            EddiEnvironmentConfig(
                agents=[self.agent_a],
                groups=[group],
            )

    def test_unknown_group_member(self):
        group = GroupConfig(
            name="group-a",
            style=next(iter(DiscussionStyle)),
            members=[GroupMemberConfig(agent="unknown-agent")],
        )

        with self.assertRaisesRegex(ValidationError, "references unknown agents"):
            EddiEnvironmentConfig(
                agents=[self.agent_a],
                groups=[group],
            )

    def test_unknown_moderator(self):
        group = GroupConfig(
            name="group-a",
            style=next(iter(DiscussionStyle)),
            members=[GroupMemberConfig(agent="agent-a")],
            moderator="unknown-moderator",
        )

        with self.assertRaisesRegex(ValidationError, "references unknown agents"):
            EddiEnvironmentConfig(
                agents=[self.agent_a],
                groups=[group],
            )