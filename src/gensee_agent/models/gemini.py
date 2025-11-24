import os
from typing import AsyncGenerator, Sequence

from google import genai
from google.genai.types import Content, ContentListUnion, ContentUnion, GenerateContentResponse, Part

from gensee_agent.controller.dataclass.llm_response import LLMResponses, SingleLLMResponse
from gensee_agent.controller.message_handler import MessageHandler
from gensee_agent.models.base import BaseModel, register_model_provider
from gensee_agent.settings import Settings
from gensee_agent.utils.logging import configure_logger

logger = configure_logger(__name__)

class GeminiModel(BaseModel):
    def __init__(self, model_name: str, config: dict):
        super().__init__(model_name, config)
        self.api_key = os.environ.get("GEMINI_API_KEY")
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = model_name.split(Settings.SEPARATOR, maxsplit=1)[-1]
        self.message_handler = MessageHandler(config={})


    def _convert_llm_use(self, messages: list[dict]) -> list[Content]:
        """
        Input messages is a list of dict with "role" and "content" keys.
        Output messages are converted to the format expected by Gemini API:
        [
            {
                "role": "user" | "assistant" | "system",
                "parts": [{"text": "message"}]}
            },
            ...
        ]
        """
        role_mapping = {
            "user": "user",
            "assistant": "model",
            "system": "user",  # Gemini doesn't have a system role, treat as user
        }
        converted_messages = [
            Content(
                role=role_mapping.get(message["role"], "user"),
                parts=[Part(text=message["content"])]
            )
            for message in messages
        ]
        return converted_messages

    async def completion(self, messages: list) -> GenerateContentResponse:
        # Need to convert the messages to the format expected by Gemini API
        converted_messages = self._convert_llm_use(messages)
        response = await self.client.aio.models.generate_content(
            model=self.model_name,
            contents=converted_messages # pyright: ignore[reportArgumentType]
        )
        return response

    def to_llm_responses(self, response: GenerateContentResponse) -> LLMResponses:
        if not isinstance(response, GenerateContentResponse):
            raise ValueError("Response is not of type GenerateContentResponse.")

        # logger.info(f"Received response from Gemini: {response}")

        title = self.message_handler.extract_title(response.text or "")
        return [
            SingleLLMResponse(
                title=title or "[No Title]",
                content=response.text or "",
                finish_reason=response.candidates[0].finish_reason.name if response.candidates and response.candidates[0].finish_reason else "unknown",
                partial=False
            )
        ]

register_model_provider(f"gemini{Settings.SEPARATOR}gemini-2.5-flash", GeminiModel)
register_model_provider(f"gemini{Settings.SEPARATOR}gemini-2.5-pro", GeminiModel)
