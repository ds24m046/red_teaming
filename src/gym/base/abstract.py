from __future__ import annotations

from httpx import Client
from abc import ABC, abstractmethod
from typing import Self

from red_teaming.src.gym.base.configs import GymConfig
from red_teaming.src.gym.base.models import ChatReply, ChatRequest


class ChatSession(ABC):
    """A conversation with one agent or group."""

    @abstractmethod
    def send(self, request: ChatRequest) -> ChatReply: ...

    @abstractmethod
    def close(self) -> None: ...


class EddiServer(ABC):
    """Lifecycle of a local EDDI instance."""

    @property
    @abstractmethod
    def client(self) -> Client:
        """HTTP client bound to the EDDI base URL."""

    @abstractmethod
    def start(self) -> None:
        """Start an empty EDDI and wait until it is ready."""

    @abstractmethod
    def destroy(self) -> None:
        """Stop EDDI and delete all its data."""


class GymEnvironment(ABC):
    """An EDDI system built from one GymConfig, ready to talk to."""

    @classmethod
    @abstractmethod
    def create(cls, config: GymConfig, server: EddiServer) -> Self:
        """Start the server, provision agents/groups from config, return a running environment."""

    @abstractmethod
    def chat(self, target: str) -> ChatSession:
        """Open a chat with an agent or group by name."""

    @abstractmethod
    def close(self) -> None:
        """Destroy the server and its data."""
