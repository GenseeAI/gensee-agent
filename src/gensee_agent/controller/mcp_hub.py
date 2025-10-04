from contextlib import AsyncExitStack
from dataclasses import field

from mcp import ClientSession, StdioServerParameters, stdio_client

from gensee_agent.configs.configs import BaseConfig, register_configs

class McpHub:

    @register_configs("mcp_hub")
    class Config(BaseConfig):
        allowed_mcps: dict = field(default_factory=dict)  # Mapping of allowed MCP, in the following format:
        # {
        #   "mcp_name": {
        #       "type": "stdio",  # "stdio", "sse" or "streaming".  Currently only "stdio" is supported
        #       "description": "Description of the MCP",  # Optional
        #       "path_or_address": "/path/to/mcp/script.py or https://mcp.url/endpoint"  # Path to the MCP script or URL of the MCP endpoint
        #   }
        #   ...
        # }

        def __post_init__(self):
            if not isinstance(self.allowed_mcps, dict):
                raise ValueError("allowed_mcps must be a dictionary")

            for mcp_name, mcp_config in self.allowed_mcps.items():
                if not isinstance(mcp_name, str) or not mcp_name.strip():
                    raise ValueError(f"MCP name must be a non-empty string, got: {mcp_name}")

                if not isinstance(mcp_config, dict):
                    raise ValueError(f"MCP config for '{mcp_name}' must be a dictionary, got: {type(mcp_config)}")

                # Validate required fields
                if "type" not in mcp_config:
                    raise ValueError(f"MCP '{mcp_name}' missing required field: 'type'")

                if "path_or_address" not in mcp_config:
                    raise ValueError(f"MCP '{mcp_name}' missing required field: 'path_or_address'")

                # Validate type field
                valid_types = ["stdio", "sse", "streaming"]
                if mcp_config["type"] not in valid_types:
                    raise ValueError(f"MCP '{mcp_name}' has invalid type '{mcp_config['type']}'. Must be one of: {valid_types}")

                # Validate path_or_address field
                if not isinstance(mcp_config["path_or_address"], str) or not mcp_config["path_or_address"].strip():
                    raise ValueError(f"MCP '{mcp_name}' path_or_address must be a non-empty string")

                # Validate optional description field
                if "description" in mcp_config and not isinstance(mcp_config["description"], str):
                    raise ValueError(f"MCP '{mcp_name}' description must be a string if provided")

                # Check for unexpected fields
                allowed_fields = {"type", "description", "path_or_address"}
                unexpected_fields = set(mcp_config.keys()) - allowed_fields
                if unexpected_fields:
                    raise ValueError(f"MCP '{mcp_name}' has unexpected fields: {unexpected_fields}")

    def __init__(self, config: dict, token: str):
        assert token == "secret_token", "This class should be initialized with create() method, not directly."
        self.config = self.Config.from_dict(config)
        self.exit_stack = AsyncExitStack()
        self.mcp_meta = {}
        self.initialized = False

    @classmethod
    async def create(cls, config: dict) -> "McpHub":
        self = cls(config, token="secret_token")
        await self.init_mcp()
        return self

    async def init_mcp(self):
        for mcp_name, mcp_info in self.config.allowed_mcps.items():
            if mcp_info.get("type") != "stdio":
                raise ValueError(f"MCP type {mcp_info.get('type')} not supported yet.  Only 'stdio' is supported.")
            self.mcp_meta[mcp_name] = await self.connect_to_stdio_server(mcp_info.get("path_or_address"))
        self.initialized = True

    def get_tool_list(self) -> list:
        if not self.initialized:
            raise ValueError("MCP not initialized.  Call init_mcp() or use McpHub.create() first.")
        all_tools = []
        for mcp_name, mcp_data in self.mcp_meta.items():
            tools = mcp_data.get("tools", [])
            for tool in tools:
                # Prefix tool name with MCP name to ensure uniqueness
                tool.name = f"{mcp_name}{tool.name}"
                all_tools.append(tool)
        return all_tools

    async def connect_to_stdio_server(self, server_script_path: str) -> dict:
        """Connect to an MCP server

        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        stdio, write = stdio_transport
        session = await self.exit_stack.enter_async_context(ClientSession(stdio, write))

        await session.initialize()

        # List available tools
        response = await session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

        return {
            "stdio": stdio,
            "write": write,
            "session": session,
            "tools": tools,
        }
