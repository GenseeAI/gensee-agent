import asyncio
from dataclasses import field
import importlib.util
import json
import os
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

from gensee_agent.configs.configs import BaseConfig, register_configs
from gensee_agent.controller.dataclass.tool_use import ToolUse
from gensee_agent.controller.mcp_hub import McpHub
from gensee_agent.exceptions.gensee_exceptions import ToolExecutionError
from gensee_agent.tools.base import _TOOL_REGISTRY
from gensee_agent.tools.system_tools.mcp_tool import McpTool
from gensee_agent.tools.system_tools.user_interaction_tool import UserInteraction
from gensee_agent.settings import Settings

class ToolManager:
    @register_configs("tool_manager")
    class Config(BaseConfig):
        available_tools: list[str]  # List of available model names.
        use_mcp: bool = False  # Whether to use MCP for tool execution.
        user_tool_paths: list[str] = field(default_factory=list)  # List of paths to user-defined tool scripts.

    def __init__(self, config: dict, token: str, use_interaction: bool, interactive_callback: Optional[Callable[[str], Awaitable[str]]] = None):
        assert token == "secret_token", "This class should be initialized with create() method, not directly."
        self.config = self.Config.from_dict(config)
        self.use_interaction = use_interaction
        if self.config.user_tool_paths:
            for path in self.config.user_tool_paths:
                # Dynamically load user-defined tools from the specified paths
                for file_path in Path(path).glob("*.py"):
                    module_name = os.path.splitext(os.path.basename(file_path))[0]
                    spec = importlib.util.spec_from_file_location(module_name, file_path)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                    else:
                        raise ImportError(f"Could not load module from path: {path}")

        # Check tools are available
        for tool_name in self.config.available_tools:
            if tool_name not in _TOOL_REGISTRY:
                raise ValueError(f"Tool {tool_name} is not registered in the tool registry.")

        self.tools = {
            tool_name: _TOOL_REGISTRY[tool_name](tool_name, config)
            for tool_name in self.config.available_tools
        }
        if self.use_interaction:
            tool_name = f"system{Settings.SEPARATOR}user_interaction"
            interaction_tool = UserInteraction(tool_name, config, callback=interactive_callback)

            # Update existing tooling (not including Interaction Tool and MCP tools) to allow interactions
            for existing_tool in self.tools.values():
                existing_tool.set_interaction_func(interaction_tool.ask_followup_question)

            # Add the interaction tool to the tool manager
            self.tools[tool_name] = interaction_tool
            self.config.available_tools.append(tool_name)

    @classmethod
    async def create(cls, config: dict, use_interaction: bool, interactive_callback: Optional[Callable[[str], Awaitable[str]]] = None) -> "ToolManager":
        self = cls(config, token="secret_token", use_interaction=use_interaction, interactive_callback=interactive_callback)
        await self.init_mcp(config)
        return self

    async def init_mcp(self, config: dict):
        if self.config.use_mcp:
            self.mcp_hub = await McpHub.create(config)
            for mcp_name, mcp_meta in self.mcp_hub.mcp_meta.items():
                tool_name = f"system{Settings.SEPARATOR}mcp{Settings.SEPARATOR}{mcp_name}"
                self.tools[tool_name] = McpTool(tool_name, config, mcp_meta["tools"], mcp_meta["session"])
                self.config.available_tools.append(tool_name)
                print(f"Connected to MCP {mcp_name} with tools:", [tool.name for tool in mcp_meta.get("tools", [])])

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
                if param_value is not None and isinstance(param_value, str) and (param_value.lower() == "none" or param_value.lower() == "null"):
                    tool_use.params[param_name] = None
                    continue
            if tool._public_api_metadata[func_name]["parameters"][param_name]["type"] == "<class 'int'>" and isinstance(param_value, str):
                try:
                    tool_use.params[param_name] = int(param_value)
                except ValueError:
                    raise ToolExecutionError(f"Parameter {param_name} should be an integer, got {param_value}", retryable=False)
            # type == number is from MCP.
            if isinstance(param_value, str) and (tool._public_api_metadata[func_name]["parameters"][param_name]["type"] == "<class 'float'>" or tool._public_api_metadata[func_name]["parameters"][param_name]["type"] == "number"):
                try:
                    tool_use.params[param_name] = float(param_value)
                except ValueError:
                    raise ToolExecutionError(f"Parameter {param_name} should be a float, got {param_value}", retryable=False)
            if isinstance(param_value, str) and tool._public_api_metadata[func_name]["parameters"][param_name]["type"] == "<class 'bool'>":
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