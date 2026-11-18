from typing import Any

from pydantic import BaseModel, Field
from red_teaming.gym.enums import ConversationState


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    context: dict[str, Any] = Field(default_factory=dict)


class ToolCall(BaseModel):
    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    result: str | None = None


class ChatReply(BaseModel):
    text: str
    state: ConversationState = ConversationState.READY
    conversation_id: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)
