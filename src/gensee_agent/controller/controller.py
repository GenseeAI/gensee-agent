from typing import AsyncIterator, Awaitable, Callable, Optional
from gensee_agent.configs.configs import BaseConfig, register_configs
from gensee_agent.controller.history_manager import HistoryManager
from gensee_agent.controller.message_handler import MessageHandler
from gensee_agent.controller.llm_manager import LLMManager
from gensee_agent.controller.prompt_manager import PromptManager
from gensee_agent.controller.task_manager import TaskManager
from gensee_agent.controller.tool_manager import ToolManager

class Controller:

    @register_configs("controller")
    class Config(BaseConfig):
        name: str  # Name of the controller.
        allow_user_interaction: bool = False  # Whether to allow user interaction

    def __init__(self, config: dict, interactive_callback: Optional[Callable[[str], Awaitable[str]]] = None):
        self.config = self.Config.from_dict(config)
        self.llm_manager = LLMManager(config)
        if self.config.allow_user_interaction:
            if interactive_callback is None:
                raise ValueError("interactive_callback must be provided if allow_user_interaction is True")
            self.tool_manager = ToolManager(config, interactive_callback=interactive_callback)
        else:
            self.tool_manager = ToolManager(config)
        self.profile = None
        self.prompt_manager = PromptManager(config)
        self.message_handler = MessageHandler(config)
        self.interactive_callback = interactive_callback

    async def run(self, task: str) -> AsyncIterator[str]:
        self.config.pretty_print()
        self.llm_manager.config.pretty_print()
        self.prompt_manager.config.pretty_print()
        print(f"Available tools: {self.tool_manager.tools.keys()}")
        print(f"Controller {self.config.name} is running...")

        task_manager = TaskManager(
            llm_manager=self.llm_manager,
            tool_manager=self.tool_manager,
            prompt_manager=self.prompt_manager,
            message_handler=self.message_handler,
            allow_interaction=self.config.allow_user_interaction,
        )

        task_manager.create_task(task, history_manager=HistoryManager())
        async for chunk in task_manager.start():
            yield chunk
