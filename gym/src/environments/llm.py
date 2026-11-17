import uuid

from red_teaming.gym.base import BaseEnvironment
from red_teaming.gym.src.servers.llm import LLMServer
from red_teaming.gym.src.sessions.llm import LLMSession
from red_teaming.gym.configs.environments.llm import LLMEnvironmentConfig


class LLMEnvironment(BaseEnvironment):
    
    def __init__(self, config: LLMEnvironmentConfig):
        
        self.config = config        
        self.server = None
        
        self._id = None
        self._sessions: list[LLMSession] = []
    
    def create(self) -> "LLMEnvironment":
        
        self.server = LLMServer(self.config.server)
        self.server.start()

        self._id = str(uuid.uuid4())
        
        return self
    
    def chat(self, target: str) -> LLMSession:
        
        if target != self._id:
            raise ValueError(f"Unknown target: {target}")

        self.server._config.openai_deployment
        
        session = LLMSession(
            self.server.client,
            self.server._config.openai_deployment,
            self.config.system_prompt
        )
        
        self._sessions.append(session)
        
        return session

    def close(self) -> None:
        
        for session in self._sessions:
            session.close()
        
        self.server.destroy()
        
        self._id = None
        self.server = None
        self._sessions.clear()
        