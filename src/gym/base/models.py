from typing import Any
from pydantic import BaseModel, Field

from red_teaming.src.gym.base.enums import ConversationState


class ChatRequest(BaseModel):
    """User input to an agent or group, with optional context key-values."""

    message: str = Field(min_length=1)
    context: dict[str, Any] = Field(default_factory=dict)


class ToolCall(BaseModel):
    """A tool call made by an agent while answering."""

    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    result: str | None = None


class ChatReply(BaseModel):
    """Answer to one chat message."""

    text: str
    state: ConversationState = ConversationState.READY
    conversation_id: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)
