from typing import Awaitable, Callable, Optional

from gensee_agent.configs.configs import BaseConfig, register_configs
from gensee_agent.exceptions.gensee_exceptions import ToolExecutionError, ShouldStop
from gensee_agent.tools.base import BaseTool, public_api

class UserInteraction(BaseTool):

    @register_configs("user_interaction")
    class Config(BaseConfig):
        enable_interaction_without_callback: bool = False  # Whether to allow interaction without a callback. It will ask LLM to stop execution.

    def __init__(self, tool_name: str, config: dict, callback: Optional[Callable[[str], Awaitable[str]]] = None):
        super().__init__(tool_name, config)
        self.config = self.Config.from_dict(config)
        if not self.config.enable_interaction_without_callback and callback is None:
            raise ValueError("Callback must be provided if allow_user_interaction is True")
        self.callback = callback

    @public_api
    async def ask_followup_question(self, question: str, options: str = "") -> str:

        """Ask the user a follow-up question and get their response.
        Args:
            question (str): The question to ask the user.
            options (str): Optional comma-separated list of options for the user to choose from: for example, "Yes,No", default is no options.
        Returns:
            str: The user's response.
        """
        if self.config.enable_interaction_without_callback:
            error_message = f"User interaction is required. \n<user_interaction>\n<question>{question}</question>\n<options>{options}</options>\n</user_interaction>"
            raise ShouldStop(error_message, retryable=False)
        try:
            assert self.callback is not None, "Callback must be provided for user interaction."
            user_input = await self.callback(question)
            return user_input
        except Exception as e:
            raise ToolExecutionError(f"Error during user interaction: {e}", retryable=True)

# No need to register for system tools as they will be initialized manually.
