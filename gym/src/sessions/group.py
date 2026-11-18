import json

from httpx import Client
from red_teaming.gym.base import BaseSession
from red_teaming.gym.enums import ConversationState
from red_teaming.gym.models import ChatReply, ChatRequest


class GroupSession(BaseSession):
    def __init__(self, client: Client, group_id: str):

        self._client = client
        self._group_id = group_id
        self._closed = False

    def send(self, request: ChatRequest) -> ChatReply:

        if self._closed:
            raise RuntimeError("Session is closed")

        response = self._client.post(
            f"/groups/{self._group_id}/conversations", json={"question": request.message}
        )
        response.raise_for_status()

        raw = response.json() if response.content else {}
        text = raw.get("decision") or raw.get("synthesizedAnswer") or json.dumps(raw)

        reply = ChatReply(
            text=str(text),
            state=ConversationState(raw.get("conversationState", "READY")),
            conversation_id=raw.get("id"),
            raw=raw,
        )

        return reply

    def close(self) -> None:

        self._closed = True
