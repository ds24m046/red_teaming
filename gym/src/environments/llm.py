import uuid
import logging

from red_teaming.gym.base import BaseEnvironment
from red_teaming.gym.src.servers.llm import LLMServer
from red_teaming.gym.src.sessions.llm import LLMSession
from red_teaming.gym.configs.environments.llm import LLMEnvironmentConfig


logger = logging.getLogger(__name__)

class LLMEnvironment(BaseEnvironment):
    
    def __init__(self, config: LLMEnvironmentConfig):
        
        self.config = config        
        self.server = None
        
        self._id = None
        self._sessions: list[LLMSession] = []
    
    def create(self) -> "LLMEnvironment":
        
        if self.server is not None:
            raise RuntimeError("Environment has already been created")

        self.server = LLMServer(self.config.server)

        try:
            self.server.start()
            self._id = str(uuid.uuid4())
        except Exception:
            self.server.destroy()
            self.server = None
            self._id = None
            raise

        return self
    
    def chat(self, target: str) -> LLMSession:
        
        if target != self._id:
            raise ValueError(f"Unknown target: {target}")
        
        session = LLMSession(
            self.server.client,
            self.server.deployment,
            self.config.system_prompt
        )
        
        self._sessions.append(session)
        
        return session

    def close(self) -> None:
        
        try:
            
            for session in self._sessions:
                try:
                    session.close()
                except Exception:
                    logger.exception("Failed to close session")
        
        finally:        
            
            if self.server is not None:
                self.server.destroy()
                self.server = None

            self._id = None
            self._sessions.clear()
        