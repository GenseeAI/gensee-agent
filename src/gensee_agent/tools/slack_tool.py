import asyncio
from typing import Any, Optional
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError

from gensee_agent.utils.configs import BaseConfig, register_configs
from gensee_agent.exceptions.gensee_exceptions import ToolExecutionError
from gensee_agent.settings import Settings
from gensee_agent.tools.base import BaseTool, register_tool, public_api

class SlackTool(BaseTool):

    @register_configs("slack_tool")
    class Config(BaseConfig):
        slack_bot_token: str  # Slack bot token for authentication, "xoxb-..."
        max_retries: int = 5  # Maximum number of retries for API calls
        max_channel_size: int = 200  # Maximum number of channels to retrieve in list_channels
        max_channel_history: int = 200  # Maximum number of messages to retrieve in fetch_channel_history

    def __init__(self, tool_name: str, config: dict):
        super().__init__(tool_name, config)
        self.config = self.Config.from_dict(config)
        self.client = AsyncWebClient(token=self.config.slack_bot_token)

    async def call_with_backoff(self, fn, *args, **kwargs):
        """Call an async Slack API fn with 429/5xx backoff."""
        backoff = 1.0
        retries = 0
        while True:
            retries += 1
            if retries > self.config.max_retries:
                raise ToolExecutionError("Max retries exceeded", retryable=False)
            try:
                return await fn(*args, **kwargs)
            except SlackApiError as e:
                status = getattr(e.response, "status_code", None)
                # Handle rate limit
                if status == 429:
                    retry_after = int(e.response.headers.get("Retry-After", "1"))
                    await asyncio.sleep(retry_after)
                    continue
                # Transient server/network errors
                if status and 500 <= status < 600:
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, 30)
                    continue
                raise ToolExecutionError(f"Slack API error: {e}", retryable=False)

    @public_api
    async def list_channels(self, channel_types: str = "public_channel,private_channel") -> list[dict[str, Any]]:
        """List all channels in the Slack workspace.

        Args:
            channel_types (str): Comma-separated list of channel types to include.
                                 Options include "public_channel", "private_channel", "mpim", "im".

        Returns:
            list[dict[str, Any]]: List of channel objects.
        """
        channels: list[dict[str, Any]] = []
        cursor: Optional[str] = None
        while True:
            resp = await self.call_with_backoff(
                self.client.conversations_list, limit=200, cursor=cursor, types=channel_types
            )
            channels.extend(resp.get("channels", []))
            cursor = resp.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break
        return channels

    @public_api
    async def fetch_channel_history(
        self,
        channel_id: str,
        oldest: Optional[str] = None,
        latest: Optional[str] = None,
        include_threads: bool = True,
        limit: int = 500   # Max 1000
    ) -> list[dict[str, Any]]:
        """Fetch up to `limit` messages from a channel, return as JSON-encoded list.

        Args:
            channel_id (str): ID of the channel to fetch messages from.
            oldest (str, optional): Start time (inclusive) as a Unix timestamp string.
            latest (str, optional): End time (inclusive) as a Unix timestamp string.
            include_threads (bool): Whether to include thread replies.
            limit (int): Maximum number of messages to retrieve (Max: 1000).

        Returns:
            list[dict[str, Any]]: message objects.

        """
        all_msgs: list[dict[str, Any]] = []
        cursor: Optional[str] = None

        if limit > 1000:
            limit = 1000

        while True:
            resp = await self.call_with_backoff(
                self.client.conversations_history,
                channel=channel_id,
                cursor=cursor,
                limit=self.config.max_channel_history,
                inclusive=True,
                oldest=oldest,
                latest=latest,
            )
            msgs = resp.get("messages", [])
            all_msgs.extend(msgs)

            # fetch thread replies if requested
            if include_threads:
                for m in msgs:
                    if m.get("thread_ts") and m.get("reply_count", 0) > 0:
                        replies = await self.fetch_thread_replies(channel_id, m["thread_ts"])
                        all_msgs.extend(replies)

            cursor = resp.get("response_metadata", {}).get("next_cursor")
            if not cursor or len(all_msgs) >= limit:
                break

        return all_msgs[:limit]

    @public_api
    async def fetch_thread_replies(self, channel_id: str, thread_ts: str) -> list[dict[str, Any]]:
        """Fetch all replies in a thread.

        Args:
            channel_id (str): ID of the channel containing the thread.
            thread_ts (str): Timestamp of the parent message of the thread.

        Returns:
            list[dict[str, Any]]: List of message objects in the thread.
        """
        replies: list[dict[str, Any]] = []
        cursor: Optional[str] = None

        while True:
            resp = await self.call_with_backoff(
                self.client.conversations_replies,
                channel=channel_id,
                ts=thread_ts,
                cursor=cursor,
                limit=200,
            )
            replies.extend(resp.get("messages", []))
            cursor = resp.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break

        return replies


register_tool(f"gensee{Settings.SEPARATOR}slack_tool", SlackTool)