import inspect

from docstring_parser import parse

_TOOL_REGISTRY : dict[str, type["BaseTool"]] = {}

class BaseTool:

    _public_api_metadata: dict[str, dict] = {}

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()

        cls._public_api_metadata = {}
        for name, func in cls.__dict__.items():
            if callable(func) and getattr(func, "_is_public_api", False):
                signature = inspect.signature(func)
                doc = parse(inspect.getdoc(func) or "")

                properties = {}
                signature_params = [p for p in signature.parameters.values() if p.name != "self"]
                assert len(signature_params) == len(doc.params), f"Method {name} has {len(signature_params)} parameters but {len(doc.params)} documented parameters."
                for param, doc_param in zip(signature_params, doc.params):
                    properties[param.name] = {
                        "type": str(param.annotation) if param.annotation != inspect.Parameter.empty else (doc_param.type_name or "Any"),
                        "description": doc_param.description if doc_param else "",
                        "required": param.default == inspect.Parameter.empty,
                    }

                cls._public_api_metadata[name] = {
                    "function": func,
                    "description": doc.short_description if doc else "",
                    "parameters": properties,
                }

    def __init__(self, tool_name: str, config: dict):
        pass

def register_tool(tool_name: str, tool_class: type[BaseTool]):
    assert tool_name is not None and tool_name != "", "tool_name should not be empty."
    assert tool_name not in _TOOL_REGISTRY, f"tool_name {tool_name} already registered."
    assert issubclass(tool_class, BaseTool), "tool_class should be a subclass of BaseTool."
    _TOOL_REGISTRY[tool_name] = tool_class

def public_api(func):
    func._is_public_api = True
    return func
