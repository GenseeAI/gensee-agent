import asyncio
from typing import Any

from gensee_agent.configs.configs import BaseConfig, register_configs
from gensee_agent.controller.dataclass.tool_use import ToolUse
from gensee_agent.tools.base import _TOOL_REGISTRY
from gensee_agent.settings import Settings

class ToolManager:
    @register_configs("tool_manager")
    class Config(BaseConfig):
        available_tools: list[str]  # List of available model names.

        def __post_init__(self):
            for model_name in self.available_tools:
                if model_name not in _TOOL_REGISTRY:
                    raise ValueError(f"Tool {model_name} is not registered in the tool registry.")

    def __init__(self, config: dict):
        self.config = self.Config.from_dict(config)
        self.tools = {
            tool_name: _TOOL_REGISTRY[tool_name](tool_name, config)
            for tool_name in self.config.available_tools
        }
        self.tool_descriptions = self.get_tool_descriptions()

    def get_tool_descriptions(self) -> str:
        descriptions = []
        for tool_name, tool_func in self.tools.items():
            for api_name, api_metadata in tool_func._public_api_metadata.items():
                unique_tool_name = f"{tool_name}{Settings.SEPARATOR}{api_name}"
                tool_description = api_metadata.get("description", "")
                tool_parameters = []
                for param_name, param_data in api_metadata.get("parameters", {}).items():
                    option_or_required = "required" if param_data.get("required", False) else "optional"
                    tool_parameters.append(
                        f"- {param_name}: ({param_data.get('type', 'Any')}, {option_or_required}): {param_data.get('description', '')}")
                tool_parameters_str = "\n".join(tool_parameters)
                descriptions.append(f"## {unique_tool_name}\n"
                                    f"Description: {tool_description.strip()}\n"
                                     "Parameters:\n"
                                    f"{tool_parameters_str if tool_parameters_str else 'None'}\n")
        return "\n".join(descriptions)

    async def execute(self, tool_use: ToolUse) -> Any:

        tool_name = tool_use.tool_name()
        func_name = tool_use.func_name()
        if tool_name not in self.tools:
            raise ValueError(f"Tool {tool_name} is not available. Available tools: {self.config.available_tools}")
        tool = self.tools[tool_name]
        if func_name not in tool._public_api_metadata:
            raise ValueError(f"Function {func_name} is not a public API of tool {tool_name}. Available functions: {list(tool._public_api_metadata.keys())}")
        func = tool._public_api_metadata[func_name]["function"]
        if callable(func):
            if asyncio.iscoroutinefunction(func):
                return await func(tool, **tool_use.params)
            else:
                return func(tool, **tool_use.params)
        else:
            raise ValueError(f"{func_name} is not callable.")

    def tool_response_to_string(self, tool_use: ToolUse, tool_response: Any) -> str:
        result = f"[{tool_use.api_name}] Result:\n{tool_response}\n"
        return result