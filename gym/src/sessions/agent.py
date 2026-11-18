import uuid

from httpx import Client
from red_teaming.gym.base import BaseSession
from red_teaming.gym.models import ChatReply, ChatRequest, ConversationState
from red_teaming.gym.src.utils import id_from_location


class AgentSession(BaseSession):
    def __init__(self, client: Client, agent_id: str, env: str = "production"):

        self._client = client
        self._conversation_id = None

        uid = f"gym-{uuid.uuid4().hex[:8]}"

        response = self._client.post(
            f"/agents/{agent_id}/start", params={"environment": env, "userId": uid}
        )
        response.raise_for_status()

        self._conversation_id = id_from_location(response)

    def _parse_response(self, response: dict) -> list[str]:

        texts = []
        for entry in response.get("conversationOutputs", [])[-1:]:
            for item in entry.get("output", []):
                if isinstance(item, dict) and item.get("text"):
                    texts.append(item["text"])

        return texts

    def send(self, request: ChatRequest) -> ChatReply:

        if self._conversation_id is None:
            raise RuntimeError("Session is closed")

        context = {k: {"type": "string", "value": v} for k, v in request.context.items()}

        response = self._client.post(
            f"/agents/{self._conversation_id}", json={"input": request.message, "context": context}
        )
        response.raise_for_status()

        raw = response.json() if response.content else {}
        texts = self._parse_response(raw)

        reply = ChatReply(
            text="\n".join(texts),
            state=ConversationState(raw.get("conversationState", "READY")),
            conversation_id=self._conversation_id,
            raw=raw,
        )

        return reply

    def close(self) -> None:

        if self._conversation_id is not None:
            response = self._client.post(f"/agents/{self._conversation_id}/endConversation")
            response.raise_for_status()

            self._conversation_id = None
