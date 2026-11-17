import os
from openai import AzureOpenAI

from red_teaming.gym.base import BaseServer
from red_teaming.gym.configs.servers.llm import LLMServerConfig


class LLMServer(BaseServer):
    
    def __init__(self, config: LLMServerConfig):

        super().__init__()
        
        config = {key: os.environ[value] for key, value in config.model_dump().items()}
        
        self._config = LLMServerConfig.model_validate(config)
        self._client = None
    
    @property
    def client(self) -> AzureOpenAI:
        
        if self._client is None:
            raise RuntimeError("LLM server has not been started")
        
        return self._client
    
    def start(self) -> None:
        
        self._client = AzureOpenAI(
            api_version=self._config.openai_version,
            azure_endpoint=self._config.openai_base_url,
            api_key=self._config.openai_api_key,
            max_retries=20,
        )
    
    def destroy(self) -> None:

        self._client = None
        