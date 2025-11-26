from enum import Enum
from typing import AsyncIterator, Optional, cast
import uuid

from gensee_agent.controller.dataclass.llm_response import LLMResponses
from gensee_agent.controller.dataclass.llm_use import LLMUse
from gensee_agent.controller.dataclass.tool_use import ToolUse
from gensee_agent.controller.history_manager import HistoryManager
from gensee_agent.controller.llm_manager import LLMManager
from gensee_agent.controller.message_handler import MessageHandler
from gensee_agent.controller.prompt_manager import PromptManager
from gensee_agent.controller.tool_manager import ToolManager
from gensee_agent.exceptions.gensee_exceptions import GenseeError, ShouldStop
from gensee_agent.utils.streaming_data import StreamingData
from gensee_agent.utils.logging import configure_logger

logger = configure_logger(__name__)

class TaskState:
    IDLE = 0
    INITIALIZED = 1
    RUNNING_GENERIC = 10
    RUNNING_LLM = 11
    RUNNING_TOOL = 12
    COMPLETED = 20
    ERROR = 30

    def __init__(self, state: int = IDLE):
        self.state = state

    def set(self, state: int):
        self.state = state

    def get(self) -> int:
        return self.state

    def is_running(self) -> bool:
        return self.state in {TaskState.RUNNING_GENERIC, TaskState.RUNNING_LLM, TaskState.RUNNING_TOOL}

class Action(Enum):
    NONE = 0
    LLM_USE = 1
    TOOL_USE = 2
    PARSE_LLM = 3
    PARSE_TOOL = 4

class TaskManager:
    def __init__(self, *,
                 llm_manager: LLMManager, tool_manager: ToolManager, prompt_manager: PromptManager, message_handler: MessageHandler,
                 allow_interaction: bool,
                 streaming: bool):
        self.task_id = uuid.uuid4().hex
        self.task_state = TaskState(TaskState.IDLE)
        self.llm_manager = llm_manager
        self.tool_manager = tool_manager
        self.prompt_manager = prompt_manager
        self.message_handler = message_handler
        self.next_action = Action.NONE
        self.allow_interaction = allow_interaction
        self.streaming = streaming  # Not used yet

    async def create_task(self, title: str, prompt: str, history_manager: HistoryManager, *, model_name: Optional[str] = None, use_tool: bool = True, additional_context: Optional[str] = None):
        # TODO: Haven't used history yet.
        self.history_manager = history_manager
        await self.history_manager.read_history()

        if history_manager.entry_count() == 0:
            # New task, so we need to generate the initial prompt.
            system_prompt = self.prompt_manager.generate_system_prompt_from_template(
                user_objective=prompt,
                tool_descriptions=self.tool_manager.tool_descriptions,
                allow_interaction=self.allow_interaction,
                use_tool=use_tool,
                additional_context=additional_context,
            )
            llm_use = LLMUse(prompts=[system_prompt], model_name=model_name)
            llm_use.append_user_prompt(prompt, title=title)
            await self.history_manager.add_entry("llm_use", title=title, entry=llm_use)
        else:
            llm_use = self.history_manager.get_last_entry_of_type("llm_use")
            if llm_use is None:
                raise ValueError("No previous LLM use found in history.")
            llm_use = cast(LLMUse, llm_use)
            llm_use.append_user_prompt(prompt, title=title)  # TODO(shengqi): Make the title unique.
            await self.history_manager.add_entry("llm_use", title=title, entry=llm_use)

        self.next_action = Action.LLM_USE
        self.task_state.set(TaskState.INITIALIZED)

    async def start(self) -> AsyncIterator[str]:

        yield StreamingData.status(
            session_id=self.task_id,
            message=self.history_manager.get_last_entry_title(),
        ).to_streaming_output()

        next_action = self.next_action
        while(next_action != Action.NONE):
            try:
                if next_action == Action.PARSE_LLM:
                    # Only output state change at LLM_USE stage, whose next stage is PARSE_LLM
                    yield StreamingData.status(
                        session_id=self.task_id,
                        message=self.history_manager.get_last_entry_title(),
                    ).to_streaming_output()
                next_action = await self.step()
            except ShouldStop as e:
                self.task_state.set(TaskState.COMPLETED)
                # logger.info(f"Task paused for user interaction: {e}"))
                yield StreamingData.assistant(
                    session_id=self.task_id,
                    message=f"Task paused for user interaction: {e}"
                ).to_streaming_output()
                return
            except GenseeError as e:
                self.task_state.set(TaskState.ERROR)
                # TODO: Check whether the error is retryable, and if so, maybe retry a few times?
                logger.error(f"Task encountered an error: {e}")
                yield StreamingData.error(
                    session_id=self.task_id,
                    message=f"Task encountered an error: {e}"
                ).to_streaming_output()
                return
        result = self.history_manager.get_last_entry_of_type("llm_response")
        if result is None:
            yield StreamingData.assistant(
                session_id=self.task_id,
                message="No result."
            ).to_streaming_output()
        else:
            result = cast(LLMResponses, result)
            if len(result) == 0 or result[-1].content is None:
                yield StreamingData.assistant(
                    session_id=self.task_id,
                    message="No result."
                ).to_streaming_output()
            else:
                yield StreamingData.assistant(
                    session_id=self.task_id,
                    message=result[-1].content
                ).to_streaming_output()

    async def step(self) -> Action:
        if self.task_state.get() == TaskState.ERROR:
            raise ValueError("Task is in error state.")
        if not self.task_state.is_running() and self.task_state.get() != TaskState.INITIALIZED:
            raise ValueError("Task is not running or initialized.")
        if self.next_action == Action.LLM_USE:
            self.task_state.set(TaskState.RUNNING_LLM)
            last_llm_use = self.history_manager.get_last_entry_of_type("llm_use")
            if last_llm_use is None:
                raise ValueError("No previous LLM use found in history.")
            last_llm_use = cast(LLMUse, last_llm_use)
            result = await self.llm_manager.completion(last_llm_use)
            await self.history_manager.add_entry("llm_response", result[-1].title, result)
            # logger.info(f"LLM response: {result}")
            self.next_action = Action.PARSE_LLM

        elif self.next_action == Action.PARSE_LLM:
            self.task_state.set(TaskState.RUNNING_GENERIC)
            last_response = self.history_manager.get_last_entry_of_type("llm_response")
            if last_response is None:
                raise ValueError("No previous LLM response found in history.")
            last_response = cast(LLMResponses, last_response)

            # Record the last LLM response to form a new llm_use message
            last_llm_use = self.history_manager.get_last_entry_of_type("llm_use")
            if last_llm_use is None:
                raise ValueError("No previous LLM use found in history.")
            last_llm_use = cast(LLMUse, last_llm_use)
            new_llm_use = last_llm_use.copy()
            if last_response[-1].content is not None:
                new_llm_use.append_assistant_prompt(last_response[-1].content)
            await self.history_manager.add_entry("llm_use", title=last_response[-1].title, entry=new_llm_use)

            if last_response and last_response[-1].content is not None:
                tool_use = self.message_handler.handle_message(last_response[-1].content)
            else:
                tool_use = None
            if tool_use is not None:
                await self.history_manager.add_entry("tool_use", title=f"Prepare to call {tool_use.title()}", entry=tool_use)
                logger.info(f"Parsed tool use: {tool_use}")
                self.next_action = Action.TOOL_USE
            else:
                # Looks to be finished.
                self.next_action = Action.NONE

        elif self.next_action == Action.TOOL_USE:
            self.task_state.set(TaskState.RUNNING_TOOL)
            last_tool_use = self.history_manager.get_last_entry_of_type("tool_use")
            if last_tool_use is None:
                raise ValueError("No previous tool use found in history.")
            last_tool_use = cast(ToolUse, last_tool_use)
            result = await self.tool_manager.execute(last_tool_use)
            await self.history_manager.add_entry("tool_response", title=f"Getting result of {last_tool_use.title()}", entry=result)
            logger.info(f"Tool response: {result}")
            self.next_action = Action.PARSE_TOOL

        elif self.next_action == Action.PARSE_TOOL:
            self.task_state.set(TaskState.RUNNING_GENERIC)
            tool_response = self.history_manager.get_last_entry_of_type("tool_response")
            if tool_response is None:
                raise ValueError("No previous Tool response found in history.")
            # llm_response = self.history_manager.get_last_entry_of_type("llm_response")
            # if llm_response is None:
            #     raise ValueError("No previous LLM response found in history.")
            # llm_response = cast(LLMResponses, llm_response)

            # ---
            last_llm_use = self.history_manager.get_last_entry_of_type("llm_use")
            if last_llm_use is None:
                raise ValueError("No previous LLM use found in history.")
            last_llm_use = cast(LLMUse, last_llm_use)
            # ---
            tool_use = self.history_manager.get_last_entry_of_type("tool_use")
            if tool_use is None:
                raise ValueError("No previous tool use found in history.")
            tool_use = cast(ToolUse, tool_use)
            new_llm_use = last_llm_use.copy()
            # if llm_response[-1].content is not None:
            #     new_llm_use.append_assistant_prompt(llm_response[-1].content)
            title = f"Result of {tool_use.title()}"
            new_llm_use.append_user_prompt(self.tool_manager.tool_response_to_string(tool_use, tool_response), title=title)
            await self.history_manager.add_entry("llm_use", title=title, entry=new_llm_use)
            self.next_action = Action.LLM_USE

        else:
            self.task_state.set(TaskState.COMPLETED)
            logger.info("Task completed.")

        return self.next_action
