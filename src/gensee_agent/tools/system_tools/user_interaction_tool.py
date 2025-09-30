from typing import Awaitable, Callable, Optional

from gensee_agent.configs.configs import BaseConfig, register_configs
from gensee_agent.exceptions.gensee_exceptions import ToolExecutionError
from gensee_agent.tools.base import BaseTool, public_api

class UserInteractionTool(BaseTool):

    @register_configs("user_interaction_tool")
    class Config(BaseConfig):
        pass

    def __init__(self, tool_name: str, config: dict, callback: Optional[Callable[[str], Awaitable[str]]] = None):
        super().__init__(tool_name, config)
        self.config = self.Config.from_dict(config)
        if callback is None:
            raise ValueError("Callback must be provided if allow_user_interaction is True")
        self.callback = callback

    @public_api
    async def ask_followup_question(self, question: str) -> str:

        """Ask the user a follow-up question and get their response.
        Args:
            question (str): The question to ask the user.
        Returns:
            str: The user's response.
        """

        try:
            user_input = await self.callback(question)
            return user_input
        except Exception as e:
            raise ToolExecutionError(f"Error during user interaction: {e}", retryable=True)

# No need to register for system tools as they will be initialized manually.
