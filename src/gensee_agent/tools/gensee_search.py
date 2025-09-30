import aiohttp

from gensee_agent.configs.configs import BaseConfig, register_configs
from gensee_agent.exceptions.gensee_exceptions import ToolExecutionError
from gensee_agent.settings import Settings
from gensee_agent.tools.base import BaseTool, register_tool, public_api

class GenseeSearch(BaseTool):

    @register_configs("gensee_search")
    class Config(BaseConfig):
        gensee_api_key: str  # API key for Gensee search service

    def __init__(self, tool_name: str, config: dict):
        super().__init__(tool_name, config)
        self.config = self.Config.from_dict(config)

    @public_api
    async def search(self, query: str, num_results: int = 5) -> str:
        """Perform a search using the Gensee search service.

        Args:
            query (str): The search query.
            num_results (int): The number of search results to return.

        Returns:
            str: A formatted string containing the search results.
        """
        url = "https://platform.gensee.ai/tool/search"

        payload = {
            "query": query,
            "max_results": num_results,
            "mode": "evidence"
        }
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.config.config_key}'
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    response.raise_for_status()
                    response_json = await response.json()
                    response_json["query"] = query
                    return response_json
        except aiohttp.ClientError as e:
            print(f"Error calling endpoint: {e}")
            raise ToolExecutionError(f"Error calling endpoint: {e}", retryable=True)


register_tool(f"gensee{Settings.SEPARATOR}search", GenseeSearch)