import os
import json
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from pydantic import BaseModel

from red_teaming.gym.src.llm.model import OpenAIModel


class TestResponse(BaseModel):
    answer: str
    confidence: float


class TestOpenAIModel(unittest.TestCase):

    def setUp(self):
        
        self.env = {
            "OPENAI_API_KEY": "test-api-key",
            "OPENAI_BASE_URL": "https://test.openai.azure.com",
            "OPENAI_DEPLOYMENT": "gpt-5-mini",
            "OPENAI_VERSION": "2025-01-01-preview",
        }

        self.env_patcher = patch.dict(os.environ, self.env)
        self.env_patcher.start()

        self.load_dotenv_patcher = patch(
            "red_teaming.gym.src.llm.model.load_dotenv",
            return_value=True
        )
        self.mock_load_dotenv = self.load_dotenv_patcher.start()

        self.azure_patcher = patch(
            "red_teaming.gym.src.llm.model.AzureOpenAI"
        )
        
        self.mock_azure = self.azure_patcher.start()
        self.mock_client = self.mock_azure.return_value

        self.model = OpenAIModel()

    def tearDown(self):
        
        self.env_patcher.stop()
        self.load_dotenv_patcher.stop()
        self.azure_patcher.stop()

    def test_initialization(self):
        
        self.assertEqual(self.model.api_key, "test-api-key")
        self.assertEqual(
            self.model.endpoint,
            "https://test.openai.azure.com"
        )
        self.assertEqual(self.model.deployment, "gpt-5-mini")
        self.assertEqual(
            self.model.version,
            "2025-01-01-preview"
        )

        self.assertEqual(self.model.messages, [])

        self.mock_azure.assert_called_once_with(
            api_version="2025-01-01-preview",
            azure_endpoint="https://test.openai.azure.com",
            api_key="test-api-key",
            max_retries=20,
        )

    def test_initialization_loads_dotenv(self):
    
        OpenAIModel(dotenv_path="custom.env")

        self.mock_load_dotenv.assert_called_with("custom.env")
    
    def test_collect_without_history(self):
        
        self.model.add_message("assistant", "Previous response")

        messages = self.model._collect(
            "New question",
            include_history=False
        )

        self.assertEqual(
            messages,
            [{"role": "user", "content": "New question"}]
        )

    def test_collect_with_history(self):
        
        self.model.add_message("user", "Previous question")
        self.model.add_message("assistant", "Previous response")

        messages = self.model._collect("New question")

        self.assertEqual(len(messages), 3)
        self.assertEqual(messages[-1]["content"], "New question")

    def test_reset_messages(self):
        
        self.model.add_message("user", "Hello")
        self.model.reset_messages()

        self.assertEqual(self.model.messages, [])

    def test_add_message(self):
        
        self.model.add_message("user", "Hello")

        self.assertEqual(
            self.model.messages,
            [{"role": "user", "content": "Hello"}]
        )

    def mock_response(self, content):
        
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=content)
                )
            ]
        )

    def test_call_model_without_json(self):
        
        self.mock_client.chat.completions.create.return_value = (
            self.mock_response("Hello!")
        )

        response = self.model._call("Hi")

        self.assertEqual(response, "Hello!")

        self.mock_client.chat.completions.create.assert_called_once_with(
            messages=[{"role": "user", "content": "Hi"}],
            model="gpt-5-mini",
        )

    def test_call_model_with_json(self):
        
        json_response = '{"answer": "42", "confidence": 0.95}'

        self.mock_client.chat.completions.create.return_value = (
            self.mock_response(json_response)
        )

        response = self.model._call("Answer in JSON", is_json=True)

        self.assertEqual(response, json_response)

        self.mock_client.chat.completions.create.assert_called_once_with(
            messages=[{"role": "user", "content": "Answer in JSON"}],
            model='gpt-5-mini',
            response_format={"type": "json_object"},
        )

    def test_call_model_includes_history(self):
        
        self.model.add_message("user", "Previous question")
        self.model.add_message("assistant", "Previous answer")

        self.mock_client.chat.completions.create.return_value = (
            self.mock_response("New answer")
        )

        self.model._call("New question")

        call_args = (
            self.mock_client.chat.completions.create.call_args
        )

        messages = call_args.kwargs["messages"]

        self.assertEqual(len(messages), 3)
        self.assertEqual(messages[0]["content"], "Previous question")
        self.assertEqual(messages[-1]["content"], "New question")

    def test_call_handles_api_exception(self):
        
        self.mock_client.chat.completions.create.side_effect = (
            Exception("API error")
        )

        response = self.model._call("Hello")

        self.assertIsNone(response)

    def test_call_model_returns_string(self):
        
        self.mock_client.chat.completions.create.return_value = (
            self.mock_response("Hello!")
        )

        response = self.model.call_model("Hi")

        self.assertEqual(response, "Hello!")

        self.assertEqual(
            self.model.messages,
            [
                {"role": "user", "content": "Hi"},
                {"role": "assistant", "content": "Hello!"},
            ]
        )

    def test_call_model_without_history(self):
        self.model.add_message("user", "Previous question")

        self.mock_client.chat.completions.create.return_value = (
            self.mock_response("New answer")
        )

        self.model.call_model(
            "New question",
            include_history=False
        )

        call_args = (
            self.mock_client.chat.completions.create.call_args
        )

        messages = call_args.kwargs["messages"]

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["content"], "New question")
        self.assertEqual(len(self.model.messages), 3)

    def test_call_model_returns_validated_model(self):
        
        json_response = json.dumps({
            "answer": "42",
            "confidence": 0.95,
        })

        self.mock_client.chat.completions.create.return_value = (
            self.mock_response(json_response)
        )

        response = self.model.call_model(
            "What is the answer?",
            validator=TestResponse
        )

        self.assertIsInstance(response, TestResponse)
        self.assertEqual(response.answer, "42")
        self.assertEqual(response.confidence, 0.95)

    def test_call_model_returns_none_for_invalid_json(self):
        
        json_response = '{"answer": "42"}'

        self.mock_client.chat.completions.create.return_value = (
            self.mock_response(json_response)
        )

        response = self.model.call_model(
            "What is the answer?",
            validator=TestResponse
        )

        self.assertIsNone(response)

    def test_call_model_returns_none_on_api_error(self):
        
        self.mock_client.chat.completions.create.side_effect = (
            Exception("API error")
        )

        response = self.model.call_model("Hello")

        self.assertIsNone(response)
        self.assertEqual(self.model.messages, [])


if __name__ == "__main__":
    unittest.main()