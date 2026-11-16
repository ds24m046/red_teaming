import json
import tempfile
import unittest
from pathlib import Path
from pydantic import ValidationError

from red_teaming.gym.src.environment.enums import DiscussionStyle
from red_teaming.gym.src.environment.config import (
    AgentConfig,
    GroupConfig,
    GroupMemberConfig,
    GymConfig,
    LLMConfig,
)


class TestGymConfig(unittest.TestCase):

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

        config = GymConfig(
            name="test-gym",
            agents=[self.agent_a, self.agent_b],
            groups=[self.group],
        )

        self.assertEqual(len(config.agents), 2)
        self.assertEqual(len(config.groups), 1)

    def test_duplicate_agent_names(self):
        
        duplicate = AgentConfig(
            name="agent-a",
            system_prompt="Another agent.",
            llm=LLMConfig(model="gpt-5-mini"),
        )

        with self.assertRaisesRegex(
            ValidationError,
            "agent names must be unique",
        ):
            GymConfig(
                name="test-gym",
                agents=[self.agent_a, duplicate],
            )

    def test_duplicate_group_names(self):
        
        duplicate = GroupConfig(
            name="group-a",
            style=next(iter(DiscussionStyle)),
            members=[GroupMemberConfig(agent="agent-a")],
        )

        with self.assertRaisesRegex(
            ValidationError,
            "group names must be unique",
        ):
            GymConfig(
                name="test-gym",
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
            GymConfig(
                name="test-gym",
                agents=[self.agent_a],
                groups=[group],
            )

    def test_unknown_group_member(self):
        
        group = GroupConfig(
            name="group-a",
            style=next(iter(DiscussionStyle)),
            members=[GroupMemberConfig(agent="unknown-agent")],
        )

        with self.assertRaisesRegex(
            ValidationError,
            "references unknown agents",
        ):
            GymConfig(
                name="test-gym",
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

        with self.assertRaisesRegex(
            ValidationError,
            "references unknown agents",
        ):
            GymConfig(
                name="test-gym",
                agents=[self.agent_a],
                groups=[group],
            )

    def test_from_json(self):
        
        data = {
            "name": "test-gym",
            "agents": [
                {
                    "name": "agent-a",
                    "system_prompt": "You are agent A.",
                    "llm": {"model": "gpt-5-mini"},
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gym_config.json"
            path.write_text(json.dumps(data))

            config = GymConfig.from_json(path)

        self.assertEqual(config.name, "test-gym")
        self.assertEqual(config.agents[0].name, "agent-a")

    def test_from_json_resolves_relative_compose_path(self):
        
        data = {
            "name": "test-gym",
            "server": {
                "compose_file": "docker-compose.yml",
            },
            "agents": [
                {
                    "name": "agent-a",
                    "system_prompt": "You are agent A.",
                    "llm": {"model": "gpt-5-mini"},
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config" / "gym_config.json"
            path.parent.mkdir()
            path.write_text(json.dumps(data))

            config = GymConfig.from_json(path)

            expected = (
                path.parent / "docker-compose.yml"
            ).resolve()

        self.assertEqual(config.server.compose_file, expected)
        self.assertTrue(config.server.compose_file.is_absolute())

    def test_from_json_preserves_absolute_compose_path(self):
        
        with tempfile.TemporaryDirectory() as tmp:
            compose_path = Path(tmp) / "docker-compose.yml"

            data = {
                "name": "test-gym",
                "server": {
                    "compose_file": str(compose_path),
                },
                "agents": [
                    {
                        "name": "agent-a",
                        "system_prompt": "You are agent A.",
                        "llm": {"model": "gpt-5-mini"},
                    }
                ],
            }

            path = Path(tmp) / "gym_config.json"
            path.write_text(json.dumps(data))

            config = GymConfig.from_json(path)

        self.assertEqual(config.server.compose_file, compose_path)

    def test_from_json_invalid_json(self):
        
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gym_config.json"
            path.write_text("{ invalid json }")

            with self.assertRaises(ValidationError):
                GymConfig.from_json(path)


if __name__ == "__main__":
    unittest.main()