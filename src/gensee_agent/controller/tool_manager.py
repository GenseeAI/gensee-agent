import asyncio
import json
from typing import Any, Awaitable, Callable, Optional

from gensee_agent.configs.configs import BaseConfig, register_configs
from gensee_agent.controller.dataclass.tool_use import ToolUse
from gensee_agent.exceptions.gensee_exceptions import ToolExecutionError
from gensee_agent.tools.base import _TOOL_REGISTRY
from gensee_agent.tools.system_tools.user_interaction_tool import UserInteractionTool
from gensee_agent.settings import Settings

class ToolManager:
    @register_configs("tool_manager")
    class Config(BaseConfig):
        available_tools: list[str]  # List of available model names.

        def __post_init__(self):
            for tool_name in self.available_tools:
                if tool_name not in _TOOL_REGISTRY:
                    raise ValueError(f"Tool {tool_name} is not registered in the tool registry.")

    def __init__(self, config: dict, interactive_callback: Optional[Callable[[str], Awaitable[str]]] = None):
        self.config = self.Config.from_dict(config)
        self.tools = {
            tool_name: _TOOL_REGISTRY[tool_name](tool_name, config)
            for tool_name in self.config.available_tools
        }
        if interactive_callback is not None:
            tool_name = f"system{Settings.SEPARATOR}user_interaction_tool"
            self.tools[tool_name] = UserInteractionTool(tool_name, config, callback=interactive_callback)
            self.config.available_tools.append(tool_name)

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
            raise ToolExecutionError(f"Tool {tool_name} is not available. Available tools: {self.config.available_tools}", retryable=False)
        tool = self.tools[tool_name]
        if func_name not in tool._public_api_metadata:
            raise ToolExecutionError(f"Function {func_name} is not a public API of tool {tool_name}. Available functions: {list(tool._public_api_metadata.keys())}", retryable=False)
        func = tool._public_api_metadata[func_name]["function"]

        # Handle and parsing parameters
        for (param_name, param_value) in tool_use.params.items():
            if tool._public_api_metadata[func_name]["parameters"][param_name]["required"] is False:
                if param_value.lower() == "none" or param_value.lower() == "null":
                    tool_use.params[param_name] = None
                    continue
            if tool._public_api_metadata[func_name]["parameters"][param_name]["type"] == "<class 'int'>":
                try:
                    tool_use.params[param_name] = int(param_value)
                except ValueError:
                    raise ToolExecutionError(f"Parameter {param_name} should be an integer, got {param_value}", retryable=False)
            if tool._public_api_metadata[func_name]["parameters"][param_name]["type"] == "<class 'float'>":
                try:
                    tool_use.params[param_name] = float(param_value)
                except ValueError:
                    raise ToolExecutionError(f"Parameter {param_name} should be a float, got {param_value}", retryable=False)
            if tool._public_api_metadata[func_name]["parameters"][param_name]["type"] == "<class 'bool'>":
                if param_value.lower() in ["true", "1", "yes"]:
                    tool_use.params[param_name] = True
                elif param_value.lower() in ["false", "0", "no"]:
                    tool_use.params[param_name] = False
                else:
                    raise ToolExecutionError(f"Parameter {param_name} should be a boolean, got {param_value}", retryable=False)

        if callable(func):
            if asyncio.iscoroutinefunction(func):
                result = await func(tool, **tool_use.params)
            else:
                result = func(tool, **tool_use.params)
        else:
            raise ValueError(f"{func_name} is not callable.")

        if isinstance(result, dict) or isinstance(result, list):
            return json.dumps(result)
        else:
            return result

    def tool_response_to_string(self, tool_use: ToolUse, tool_response: Any) -> str:
        result = f"[{tool_use.api_name}] Result:\n{tool_response}\n"
        return result