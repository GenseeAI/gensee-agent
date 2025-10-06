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

    def __init__(self, config: dict, token: str, interactive_callback: Optional[Callable[[str], Awaitable[str]]] = None):
        assert token == "secret_token", "This class should be initialized with create() method, not directly."
        self.config = self.Config.from_dict(config)
        self.llm_manager = LLMManager(config)
        self.profile = None
        self.prompt_manager = PromptManager(config)
        self.message_handler = MessageHandler(config)
        self.interactive_callback = interactive_callback
        self.tool_manager = None
        self.history_manager = HistoryManager(config)

    @classmethod
    async def create(cls, config: dict, interactive_callback: Optional[Callable[[str], Awaitable[str]]] = None) -> "Controller":
        self = cls(config, token="secret_token", interactive_callback=interactive_callback)
        if self.config.allow_user_interaction:
            if interactive_callback is None:
                raise ValueError("interactive_callback must be provided if allow_user_interaction is True")
            self.tool_manager = await ToolManager.create(config, interactive_callback=interactive_callback)
        else:
            self.tool_manager = await ToolManager.create(config)
        return self

    async def run(self, task: str, additional_context: str = None) -> AsyncIterator[str]:
        assert isinstance(self.tool_manager, ToolManager)

        self.config.pretty_print()
        self.llm_manager.config.pretty_print()
        self.prompt_manager.config.pretty_print()
        print(f"Available tools: {list(self.tool_manager.tools.values()) if hasattr(self.tool_manager, 'tools') and self.tool_manager.tools else []}")
        print(f"Controller {self.config.name} is running...")

        task_manager = TaskManager(
            llm_manager=self.llm_manager,
            tool_manager=self.tool_manager,
            prompt_manager=self.prompt_manager,
            message_handler=self.message_handler,
            allow_interaction=self.config.allow_user_interaction,
        )

        task_manager.create_task(task, history_manager=HistoryManager(self.history_manager.config.to_dict()), additional_context=additional_context)
        async for chunk in task_manager.start():
            yield chunk
