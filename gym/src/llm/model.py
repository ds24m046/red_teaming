import logging
import os

from dotenv import load_dotenv
from openai import APIError, APITimeoutError, AzureOpenAI, RateLimitError
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)


class OpenAIModel:
    def __init__(self, dotenv_path: str = ".env"):

        super().__init__()

        is_loaded = load_dotenv(dotenv_path)
        print(f"Loaded .env file: {is_loaded}")

        self.api_key = os.environ["OPENAI_API_KEY"]
        self.endpoint = os.environ["OPENAI_BASE_URL"]
        self.deployment = os.environ["OPENAI_DEPLOYMENT"]
        self.version = os.environ["OPENAI_VERSION"]

        self.client = AzureOpenAI(
            api_version=self.version,
            azure_endpoint=self.endpoint,
            api_key=self.api_key,
            max_retries=20,
        )

        self.messages = []

    def _collect(self, prompt: str, include_history: bool = True) -> list[dict[str, str]]:

        messages = []

        if include_history:
            messages.extend(self.messages)

        messages.append({"role": "user", "content": prompt})

        return messages

    def _call(self, prompt: str, is_json: bool = False, include_history: bool = True) -> str | None:

        messages = self._collect(prompt, include_history=include_history)

        try:
            payload = {
                "messages": messages,
                "model": self.deployment,
            }

            if is_json:
                payload["response_format"] = {"type": "json_object"}

            response = self.client.chat.completions.create(**payload)
            content = response.choices[0].message.content

            return content

        except (APIError, APITimeoutError, RateLimitError):
            logger.exception("OpenAI API error")
            return None

    def reset_messages(self) -> None:

        self.messages = []

    def add_message(self, role: str, content: str) -> None:

        self.messages.append({"role": role, "content": content})

    def call_model(
        self, message: str, include_history: bool = True, validator: type[BaseModel] | None = None
    ) -> str | BaseModel | None:

        is_json = validator is not None
        response = self._call(prompt=message, is_json=is_json, include_history=include_history)

        if response is None:
            return None

        self.add_message(role="user", content=message)
        self.add_message(role="assistant", content=response)

        if not is_json:
            return response

        try:
            return validator.model_validate_json(response)
        except ValidationError as e:
            print(f"OpenAI validation error: {e}")
            return None
