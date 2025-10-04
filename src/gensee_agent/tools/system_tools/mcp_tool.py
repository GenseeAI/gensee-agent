import functools
from typing import Any

from mcp import ClientSession, Tool

from gensee_agent.configs.configs import BaseConfig, register_configs
from gensee_agent.exceptions.gensee_exceptions import ToolExecutionError
from gensee_agent.tools.base import BaseTool

class McpTool(BaseTool):

    @register_configs("mcp_tool")
    class Config(BaseConfig):
        pass

    async def tool_callback(self, api_name: str, **kwargs) -> Any:
        try:
            response = await self.session.call_tool(api_name, arguments=kwargs)
            if response.isError:
                raise ToolExecutionError(f"MCP tool {api_name} returned an error: {response.content}", retryable=False)
            if not response.content:
                raise ToolExecutionError(f"MCP tool {api_name} returned empty response", retryable=False)
            if len(response.content) != 1:
                raise ToolExecutionError(f"MCP tool {api_name} returned multiple values, expected exactly one", retryable=False)
            if response.content[0].type != 'text':
                raise ToolExecutionError(f"MCP tool {api_name} returned non-text response, expected text", retryable=False)
            return response.content[0].text
        except Exception as e:
            raise ToolExecutionError(f"Error calling MCP tool {api_name}: {e}", retryable=False)

    def __init__(self, tool_name: str, config: dict, tools: list[Tool], session: ClientSession):

        super().__init__(tool_name, config)
        self.config = self.Config.from_dict(config)
        self.session = session

        for tool in tools:
            api_name = tool.name
            description = tool.description or ""
            parameters = {}

            assert tool.inputSchema["type"] == "object", "Only object type inputSchema is supported."
            required_input = tool.inputSchema.get("required", [])
            for param_name, param_schema in tool.inputSchema["properties"].items():
                assert "$" not in param_name, "Parameter names with dollar sign are not supported."
                parameters[param_name] = {
                    "type": param_schema.get("type", "Any"),
                    "description": param_schema.get("title", ""),
                    "required": param_name in required_input,
                }
            self._public_api_metadata[api_name] = {
                "function": functools.partial(McpTool.tool_callback, api_name=api_name),  # Use unbounded version to keep the self argument.
                "description": description,
                "parameters": parameters,
            }
