from openai import APIError, AzureOpenAI

from red_teaming.gym.base import BaseSession
from red_teaming.gym.models import ChatReply, ChatRequest, ConversationState


class LLMSession(BaseSession):

    def __init__(self, client: AzureOpenAI, deployment: str, system_prompt: str):
        
        self.client = client
        self.deployment = deployment
        
        self._messages = [
            {"role": "system", "content": system_prompt}
        ]

    def send(self, request: ChatRequest) -> ChatReply:

        self._messages.append({"role": "user", "content": request.message})

        try:
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=self._messages,
            )
            
            text = response.choices[0].message.content

            if text is None:
            
                self._messages.append({"role": "assistant", "content": "No response from model"})
            
                return ChatReply(
                    text="No response from model",
                    state=ConversationState.ERROR,
                    raw={},
                )

            self._messages.append({"role": "assistant", "content": text})

            return ChatReply(
                text=text,
                state=ConversationState.READY,
                raw=response.model_dump(),
            )

        except APIError as exc:
            
            self._messages.append({"role": "assistant", "content": str(exc)})
            
            return ChatReply(
                text=str(exc),
                state=ConversationState.ERROR,
                raw={},
            )

    def close(self) -> None:
        self._messages.clear()
