from red_teaming.gym.base import BaseConfig


class LLMServerConfig(BaseConfig):
    openai_api_key: str = "OPENAI_API_KEY"
    openai_base_url: str = "OPENAI_BASE_URL"
    openai_deployment: str = "OPENAI_DEPLOYMENT"
    openai_version: str = "OPENAI_VERSION"
