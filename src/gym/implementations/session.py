import json
import uuid

from httpx import Client, Response

from red_teaming.src.gym.base.abstract import ChatSession
from red_teaming.src.gym.base.enums import ConversationState
from red_teaming.src.gym.base.models import ChatReply, ChatRequest


def _id_from_location(response: Response) -> str:
    
    location = response.headers["Location"]
    uid = location.rstrip("/").rsplit("/", 1)[-1]
    
    return uid


class AgentChatSession(ChatSession):

    def __init__(
        self,
        client: Client,
        agent_id: str,
        user_id: str | None = None,
        environment: str = "production"
    ) -> None:
        
        self._client = client
        user_id = user_id or f"gym-{uuid.uuid4().hex[:8]}"
        
        response = self._client.post(f"/agents/{agent_id}/start", params={"environment": environment, "userId": user_id})
        response.raise_for_status()
        
        self._conversation_id = _id_from_location(response)

    def _parse_response(self, response: dict) -> list[str]:
          
        texts = []
        for entry in response.get("conversationOutputs", [])[-1:]:          
            for item in entry.get("output", []):
                if isinstance(item, dict) and item.get("text"):
                    texts.append(item["text"])
        
        return texts
    
    def send(self, request: ChatRequest) -> ChatReply:
        
        context = {k: {"type": "string", "value": v} for k, v in request.context.items()}
        
        response = self._client.post(f"/agents/{self._conversation_id}", json={"input": request.message, "context": context})
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
        
        self._client.post(f"/agents/{self._conversation_id}/endConversation")


class GroupChatSession(ChatSession):

    def __init__(self, client: Client, group_id: str) -> None:
        
        self._client = client
        self._group_id = group_id

    def send(self, request: ChatRequest) -> ChatReply:
    
        response = self._client.post(f"/groups/{self._group_id}/conversations", json={"question": request.message})
        response.raise_for_status()
        
        raw = response.json() if response.content else {}
        
        text = raw.get("decision") or raw.get("synthesizedAnswer") or json.dumps(raw)
        reply = ChatReply(text=str(text), conversation_id=raw.get("id"), raw=raw)
        
        return reply
    
    def close(self) -> None:
        pass
