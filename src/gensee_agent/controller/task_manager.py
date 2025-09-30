from enum import Enum
from typing import AsyncIterator, cast
import uuid

from gensee_agent.controller.dataclass.llm_response import LLMResponses
from gensee_agent.controller.dataclass.llm_use import LLMUse
from gensee_agent.controller.dataclass.tool_use import ToolUse
from gensee_agent.controller.history_manager import HistoryManager
from gensee_agent.controller.llm_manager import LLMManager
from gensee_agent.controller.message_handler import MessageHandler
from gensee_agent.controller.prompt_manager import PromptManager
from gensee_agent.controller.tool_manager import ToolManager
from gensee_agent.exceptions.gensee_exceptions import GenseeError

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
    def __init__(self, *, llm_manager: LLMManager, tool_manager: ToolManager, prompt_manager: PromptManager, message_handler: MessageHandler, allow_interaction: bool):
        self.task_id = uuid.uuid4().hex
        self.task_description = ""
        self.task_state = TaskState(TaskState.IDLE)
        self.llm_manager = llm_manager
        self.tool_manager = tool_manager
        self.prompt_manager = prompt_manager
        self.message_handler = message_handler
        self.next_action = Action.NONE
        self.allow_interaction = allow_interaction

    def create_task(self, task_description: str, history_manager: HistoryManager):
        # TODO: Haven't used history yet.
        self.history_manager = history_manager
        self.task_description = task_description
        assert history_manager.entry_count() == 0, "History should be empty when creating a new task.  Not supporting resuming yet."

        system_prompt = self.prompt_manager.generate_system_prompt_from_template(
            user_objective=task_description,
            tool_descriptions=self.tool_manager.tool_descriptions,
            allow_interaction=self.allow_interaction
        )
        # print(f"System prompt: {system_prompt['content']}")
        llm_use = LLMUse(prompts=[system_prompt])
        llm_use.append_user_prompt(task_description)
        self.history_manager.add_entry("llm_use", llm_use)
        self.next_action = Action.LLM_USE
        self.task_state.set(TaskState.INITIALIZED)

    async def start(self) -> AsyncIterator[str]:
        next_action = self.next_action
        while(next_action != Action.NONE):
            try:
                action_messages = {
                    Action.LLM_USE: "Calling language model...",
                    Action.TOOL_USE: "Executing tool...",
                    Action.PARSE_LLM: "Processing language model response...",
                    Action.PARSE_TOOL: "Processing tool response...",
                    Action.NONE: "Task completed."
                }
                yield action_messages.get(next_action, f"Unknown action: {next_action}")
                next_action = await self.step()
            except GenseeError as e:
                self.task_state.set(TaskState.ERROR)
                # TODO: Check whether the error is retryable, and if so, maybe retry a few times?
                print(f"Task encountered an error: {e}")
                yield f"Task encountered an error: {e}"
                return
        result = self.history_manager.get_last_entry_of_type("llm_response")
        if result is None:
            yield "No result."
        else:
            result = cast(LLMResponses, result)
            if len(result) == 0 or result[-1].content is None:
                yield "No result."
            else:
                yield result[-1].content

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
            self.history_manager.add_entry("llm_response", result)
            print(f"LLM response: {result}")
            self.next_action = Action.PARSE_LLM

        elif self.next_action == Action.PARSE_LLM:
            self.task_state.set(TaskState.RUNNING_GENERIC)
            last_response = self.history_manager.get_last_entry_of_type("llm_response")
            if last_response is None:
                raise ValueError("No previous LLM response found in history.")
            last_response = cast(LLMResponses, last_response)

            if last_response and last_response[-1].content is not None:
                tool_use = self.message_handler.handle_message(last_response[-1].content)
            else:
                tool_use = None

            if tool_use is not None:
                self.history_manager.add_entry("tool_use", tool_use)
                print(f"Parsed tool use: {tool_use}")
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
            self.history_manager.add_entry("tool_response", result)
            print(f"Tool response: {result}")
            self.next_action = Action.PARSE_TOOL

        elif self.next_action == Action.PARSE_TOOL:
            self.task_state.set(TaskState.RUNNING_GENERIC)
            tool_response = self.history_manager.get_last_entry_of_type("tool_response")
            if tool_response is None:
                raise ValueError("No previous Tool response found in history.")
            llm_response = self.history_manager.get_last_entry_of_type("llm_response")
            if llm_response is None:
                raise ValueError("No previous LLM response found in history.")
            llm_response = cast(LLMResponses, llm_response)

            last_llm_use = self.history_manager.get_last_entry_of_type("llm_use")
            if last_llm_use is None:
                raise ValueError("No previous LLM use found in history.")
            last_llm_use = cast(LLMUse, last_llm_use)
            tool_use = self.history_manager.get_last_entry_of_type("tool_use")
            if tool_use is None:
                raise ValueError("No previous tool use found in history.")
            tool_use = cast(ToolUse, tool_use)
            new_llm_use = last_llm_use.copy()
            if llm_response[-1].content is not None:
                new_llm_use.append_assistant_prompt(llm_response[-1].content)
            new_llm_use.append_user_prompt(self.tool_manager.tool_response_to_string(tool_use, tool_response))
            self.history_manager.add_entry("llm_use", new_llm_use)
            self.next_action = Action.LLM_USE

        else:
            self.task_state.set(TaskState.COMPLETED)
            print("Task completed.")

        return self.next_action
