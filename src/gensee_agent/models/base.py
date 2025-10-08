from abc import ABC
from typing import Any, AsyncGenerator

from gensee_agent.controller.dataclass.llm_response import LLMResponses

_MODEL_REGISTRY: dict[str, type["BaseModel"]] = {}

class BaseModel(ABC):

    def __init__(self, model_name: str, config: dict):
        pass

    async def completion(self, messages: list) -> Any:
        raise NotImplementedError("This method should be overridden by subclasses.")

    async def completion_stream(self, messages: list) -> AsyncGenerator[Any, None]:
        raise NotImplementedError("This method should be overridden by subclasses.")

    def to_llm_responses(self, response: Any) -> LLMResponses:
        raise NotImplementedError("This method should be overridden by subclasses.")

def register_model_provider(model_name: str, model_class: type[BaseModel]):
    assert model_name is not None and model_name != "", "model_name should not be empty."
    assert model_name not in _MODEL_REGISTRY, f"model_name {model_name} already registered."
    assert issubclass(model_class, BaseModel), "model_class should be a subclass of BaseModel."
    _MODEL_REGISTRY[model_name] = model_class