import inspect
from typing import Awaitable, Callable

from docstring_parser import parse

from gensee_agent.exceptions.gensee_exceptions import ImplementationError, ToolExecutionError

_TOOL_REGISTRY : dict[str, type["BaseTool"]] = {}

class BaseTool:

    def __init__(self, tool_name: str, config: dict):
        self._public_api_metadata = {}
        self._interaction_func = None

        # Use self.__class__.__dict__ to get class methods, not instance attributes
        for name, func in self.__class__.__dict__.items():
            if callable(func) and getattr(func, "_is_public_api", False):
                signature = inspect.signature(func)
                doc = parse(inspect.getdoc(func) or "")

                properties = {}
                signature_params = [p for p in signature.parameters.values() if p.name != "self"]
                if len(signature_params) != len(doc.params):
                    raise ImplementationError(f"Method {name} has {len(signature_params)} parameters but {len(doc.params)} documented parameters.", retryable=False)
                for param, doc_param in zip(signature_params, doc.params):
                    properties[param.name] = {
                        "type": str(param.annotation) if param.annotation != inspect.Parameter.empty else (doc_param.type_name or "Any"),
                        "description": doc_param.description if doc_param else "",
                        "required": param.default == inspect.Parameter.empty,
                    }

                self._public_api_metadata[name] = {
                    "function": func,
                    "description": doc.short_description if doc else "",
                    "parameters": properties,
                }
        print(f"All function metadata: {self._public_api_metadata}")


    def __repr__(self) -> str:
        api_names = list(self._public_api_metadata.keys())
        return f"<Tool {self.__class__.__name__} with APIs: {api_names}>"

    def set_interaction_func(self, func: Callable[[str], Awaitable[str]]):
        self._interaction_func = func

    async def call_interaction_func(self, question: str) -> str:
        if self._interaction_func is None:
            raise ToolExecutionError("Interaction function is not set for this tool.", retryable=False)
        return await self._interaction_func(question)

def register_tool(tool_name: str, tool_class: type[BaseTool]):
    assert tool_name is not None and tool_name != "", "tool_name should not be empty."
    assert not tool_name.startswith("system"), 'tool_name should not start with "system".'
    assert tool_name not in _TOOL_REGISTRY, f"tool_name {tool_name} already registered."
    assert issubclass(tool_class, BaseTool), "tool_class should be a subclass of BaseTool."
    _TOOL_REGISTRY[tool_name] = tool_class

def public_api(func):
    func._is_public_api = True
    return func
