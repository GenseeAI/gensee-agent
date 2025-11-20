import aiohttp

from gensee_agent.utils.configs import BaseConfig, register_configs
from gensee_agent.exceptions.gensee_exceptions import ToolExecutionError
from gensee_agent.settings import Settings
from gensee_agent.tools.base import BaseTool, register_tool, public_api

class GenseeScrape(BaseTool):

    @register_configs("gensee_scrape")
    class Config(BaseConfig):
        gensee_api_key: str  # API key for Gensee scrape service

    def __init__(self, tool_name: str, config: dict):
        super().__init__(tool_name, config)
        self.config = self.Config.from_dict(config)

    @public_api
    async def scrape(self, urls: list[str], query: str) -> list[dict]:
        """Perform a scrape using the Gensee scrape service.

        Args:
            urls (list[str]): The list of URLs to scrape, will be json decoded here.
            query (str): The search query.

        Returns:
            list[dict]: A json-encoded list of dictionaries containing the scrape results, in the following format:
                [
                    {
                        "url": "https://example.com",
                        "snippets": "Snippet text...",
                        "digest": None
                    },
                    ...
                ]
        """
        url = "https://app.gensee.ai/api/search"

        payload = {
            "query": query,
            "list_urls": urls,
            "digest_all": False,
            "valid_threshold": len(urls),
            "timeout_seconds": 60,
        }
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.config.gensee_api_key}'
        }

        body = ""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    body = await response.text()
                    response.raise_for_status()
                    response_json = await response.json()
                    # Return all the values of the dict
                    return [value for _, value in response_json.items()]

        except aiohttp.ClientError as e:
            print(f"Error calling endpoint: {e}")
            print(f"Response body: {body}")
            raise ToolExecutionError(f"Error calling endpoint: {e}", retryable=True)


register_tool(f"gensee{Settings.SEPARATOR}scrape", GenseeScrape)