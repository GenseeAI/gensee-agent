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

    def __init__(self, config: dict):
        self.config = self.Config.from_dict(config)
        self.llm_manager = LLMManager(config)
        self.tool_manager = ToolManager(config)
        self.profile = None
        self.prompt_manager = PromptManager(config)
        self.message_handler = MessageHandler(config)

    async def run(self, task: str):
        self.config.pretty_print()
        self.llm_manager.config.pretty_print()
        self.prompt_manager.config.pretty_print()
        print(f"Controller {self.config.name} is running...")
        # simple_prompt = self.prompt_manager.generate_prompt_system_and_user("You are a helpful agent", "Who are you?")

        task_manager = TaskManager(
            llm_manager=self.llm_manager,
            tool_manager=self.tool_manager,
            prompt_manager=self.prompt_manager,
            message_handler=self.message_handler,
        )

        task_manager.create_task(task, history_manager=HistoryManager())
        await task_manager.start()
