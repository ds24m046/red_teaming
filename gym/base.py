from typing import Self
from pathlib import Path
from abc import ABC, abstractmethod
from pydantic import BaseModel, ConfigDict

from red_teaming.gym.models import ChatReply, ChatRequest


class BaseConfig(BaseModel):
    
    model_config = ConfigDict(extra="forbid")
    
    @classmethod
    def from_json(cls, path: Path) -> Self:
        
        path = Path(path).expanduser().resolve()
        
        config = path.read_text(encoding="utf-8")
        config = cls.model_validate_json(config)
        
        return config


class BaseServer(ABC):
    
    @abstractmethod
    def start(self) -> "BaseServer":
        pass
    
    @abstractmethod
    def destroy(self) -> None:
        pass


class BaseSession(ABC):
    
    @abstractmethod
    def send(self, request: ChatRequest) -> ChatReply:
        pass
    
    @abstractmethod
    def close(self) -> None:
        pass


class BaseEnvironment(ABC):
    
    @abstractmethod
    def create(self) -> "BaseEnvironment":
        pass
    
    @abstractmethod
    def chat(self, target: str) -> BaseSession:
        pass
    
    @abstractmethod
    def close(self) -> None:
        pass
