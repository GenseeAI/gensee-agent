from typing import AsyncGenerator
from gensee_agent.utils.configs import BaseConfig, register_configs
from gensee_agent.controller.dataclass.llm_response import LLMResponses
from gensee_agent.controller.dataclass.llm_use import LLMUse
from gensee_agent.models.base import _MODEL_REGISTRY
from gensee_agent.utils.logging import configure_logger

logger = configure_logger(__name__)

class LLMManager:
    @register_configs("llm_manager")
    class Config(BaseConfig):
        available_models: list[str]  # List of available model names.
        default_model: str  # Default model name.
        streaming: bool = False  # Whether to enable streaming mode.

        def __post_init__(self):
            if self.default_model not in self.available_models:
                raise ValueError(f"Default model {self.default_model} is not in available models {self.available_models}.")
            for model_name in self.available_models:
                if model_name not in _MODEL_REGISTRY:
                    raise ValueError(f"Model {model_name} is not registered in the model registry.")

    def __init__(self, config: dict):
        self.config = self.Config.from_dict(config)
        self.models = {
            model_name: _MODEL_REGISTRY[model_name](model_name, config)
            for model_name in self.config.available_models
        }

    async def completion(self, llm_use: LLMUse) -> LLMResponses:
        model_name = llm_use.model_name or self.config.default_model
        if model_name not in self.models:
            raise ValueError(f"Model {model_name} is not available. Available models: {self.config.available_models}")
        model = self.models[model_name]
        # logger.info(f"LLMUse Prompts: {llm_use.prompts}")
        raw_response = await model.completion(llm_use.prompts)
        # logger.info(f"Raw response: {raw_response}")
        return model.to_llm_responses(raw_response)

    # async def completion_stream(self, llm_use: LLMUse) -> AsyncGenerator[LLMResponses, None]:
    #     model_name = llm_use.model_name or self.config.default_model
    #     if model_name not in self.models:
    #         raise ValueError(f"Model {model_name} is not available. Available models: {self.config.available_models}")
    #     model = self.models[model_name]
    #     async for chunk in model.completion_stream(llm_use.prompts):
    #         yield model.to_llm_responses(chunk)