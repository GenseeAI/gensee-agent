from typing import AsyncIterator, Awaitable, Callable, Optional

from redis.asyncio import Redis, RedisCluster
from gensee_agent.utils.configs import BaseConfig, register_configs
from gensee_agent.controller.dataclass.llm_use import LLMUse
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
        streaming: bool = False  # Whether to enable streaming mode.

    def __init__(self, config: dict, token: str, interactive_callback: Optional[Callable[[str], Awaitable[str]]] = None):
        assert token == "secret_token", "This class should be initialized with create() method, not directly."
        self.raw_config = config
        self.config = self.Config.from_dict(config)
        self.llm_manager = LLMManager(config)
        self.profile = None
        self.prompt_manager = PromptManager(config)
        self.message_handler = MessageHandler(config)
        self.interactive_callback = interactive_callback
        self.tool_manager = None

    @classmethod
    async def create(cls, config: dict, interactive_callback: Optional[Callable[[str], Awaitable[str]]] = None) -> "Controller":
        self = cls(config, token="secret_token", interactive_callback=interactive_callback)
        if self.config.allow_user_interaction:
            self.tool_manager = await ToolManager.create(config, use_interaction=True, interactive_callback=interactive_callback)
        else:
            self.tool_manager = await ToolManager.create(config, use_interaction=False)
        return self

    async def run(self, title: str, task: str, *, model_name: Optional[str] = None, session_id: Optional[str] = None, additional_context: Optional[str] = None,
                  redis_client: Optional[Redis|RedisCluster] = None) -> AsyncIterator[str]:
        assert isinstance(self.tool_manager, ToolManager)

        # self.config.pretty_print()
        # self.llm_manager.config.pretty_print()
        # self.prompt_manager.config.pretty_print()
        # print(f"Available tools: {list(self.tool_manager.tools.values()) if hasattr(self.tool_manager, 'tools') and self.tool_manager.tools else []}")
        print(f"Controller {self.config.name} is running...")

        task_manager = TaskManager(
            llm_manager=self.llm_manager,
            tool_manager=self.tool_manager,
            prompt_manager=self.prompt_manager,
            message_handler=self.message_handler,
            allow_interaction=self.config.allow_user_interaction,
            streaming=self.config.streaming,
        )

        history_manager = HistoryManager(self.raw_config, session_id=session_id, redis_client=redis_client)
        await task_manager.create_task(title, task, model_name=model_name, history_manager=history_manager, additional_context=additional_context)
        async for chunk in task_manager.start():
            yield chunk

    async def append_context(self, session_id: str, title: str, role: str, prompt: str, *, model_name: Optional[str] = None, additional_context: Optional[str] = None, redis_client: Optional[Redis|RedisCluster] = None):
        history_manager = HistoryManager(self.raw_config, session_id=session_id, redis_client=redis_client)
        if role not in ["system", "user", "assistant"]:
            raise ValueError("Role must be one of 'system', 'user', or 'assistant'.")
        if role == "system":
            assert self.tool_manager is not None
            system_prompt = self.prompt_manager.generate_system_prompt_from_template(
                user_objective=prompt,
                tool_descriptions=self.tool_manager.tool_descriptions,
                allow_interaction=self.config.allow_user_interaction,
                additional_context=additional_context,
            )
            if await history_manager.read_history():
                # There is a history, so we directly update the system prompt
                llm_use: LLMUse = history_manager.get_last_entry_of_type("llm_use").copy()
            else:
                # No history, so we create a new llm_use entry
                llm_use = LLMUse([], model_name=model_name)

            llm_use.set_or_update_system_prompt(system_prompt["role"], system_prompt["content"])
            await history_manager.add_entry("llm_use", title, llm_use)
        else:
            if await history_manager.read_history():
                # There is a history, so we directly update the system prompt
                llm_use: LLMUse = history_manager.get_last_entry_of_type("llm_use").copy()
            else:
                raise ValueError("Adding user/assistant message requires system prompt to be set first.")
            if role == "user":
                llm_use.append_user_prompt(prompt, title)
            else:
                # Check if the title already exists in the prompt
                if not llm_use.has_title(prompt):
                    prompt = llm_use.add_title(prompt, title)
                llm_use.append_assistant_prompt(prompt)
        await history_manager.add_entry("llm_use", title, llm_use)
