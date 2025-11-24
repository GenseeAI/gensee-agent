import os
from typing import AsyncGenerator

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionChunk

from gensee_agent.controller.dataclass.llm_response import LLMResponses, SingleLLMResponse
from gensee_agent.controller.message_handler import MessageHandler
from gensee_agent.models.base import BaseModel, register_model_provider
from gensee_agent.settings import Settings

class OpenAIModel(BaseModel):
    def __init__(self, model_name: str, config: dict):
        super().__init__(model_name, config)
        self.api_key = os.environ.get("OPENAI_API_KEY")
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.model_name = model_name.split(Settings.SEPARATOR, maxsplit=1)[-1]
        self.message_handler = MessageHandler(config={})

    async def completion(self, messages: list) -> ChatCompletion:
        # TODO: ignore streaming for now.
        chat_completion = self.client.chat.completions.create(
            messages=messages,
            model=self.model_name)
        return await chat_completion # type: ignore

    async def completion_stream(self, messages: list) -> AsyncGenerator[ChatCompletionChunk, None]:
        stream = await self.client.chat.completions.create(
            messages=messages,
            model=self.model_name,
            stream=True)
        async for chunk in stream:
            yield chunk

    def to_llm_responses(self, response: ChatCompletion | ChatCompletionChunk) -> LLMResponses:
        if not isinstance(response, ChatCompletion):
            raise ValueError("Response is not of type ChatCompletion.")
        title = self.message_handler.extract_title(response.choices[0].message.content or "")
        return [
            SingleLLMResponse(
                title=title or "[No Title]",
                content=resp.message.content,
                finish_reason=resp.finish_reason,
                partial=False)
            for resp in response.choices]

register_model_provider(f"openai{Settings.SEPARATOR}gpt-5-mini", OpenAIModel)
register_model_provider(f"openai{Settings.SEPARATOR}gpt-5", OpenAIModel)