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
    async def ask_followup_question(self, question: str, options: str = "", multiple_choice: bool = False, actions: str = "") -> str:

        """Ask the user a follow-up question and get their response.
        Args:
            question (str): The question to ask the user.
            options (str): Optional comma-separated list of options for the user to choose from: for example, "Red, Blue", default is no options.
            multiple_choice (bool): Whether the user can select multiple options, default is False.
            actions (str | None): Optional actions that the user can take for this question. For example: "Continue, Stop".
        Returns:
            str: The user's response.
        """
        return await self.ask_multiple_followup_questions([{
            "id": 1,
            "question": question,
            "options": options,
            "multiple_choice": multiple_choice
        }], actions=actions)

    @public_api
    async def ask_multiple_followup_questions(self, questions: list[dict], prelude: str = "", actions: str = "") -> str:
        """Ask the user multiple follow-up questions and get their responses.

        Args:
            questions ((list[dict])):
                The questions to ask the user, in the following json-encoded format:
                [
                    {"id": 1, "question": "Question 1: Do you want to continue", "options": "Yes, No", "multiple_choice": false},
                    {"id": 2, "question": "Question 2: What do you want for dinner", "options": "Pizza, Salad, Sushi", "multiple_choice": true},
                    {"id": 3, "question": "Question 3: Any additional comments?"}
                    ...
                ]
                Each question can have optional options for the user to choose from, separated by commas.  `id` and `question` fields are required.
            prelude (str):
                An optional prelude message to the user before asking the questions, to provide users more context.
            actions (str | None):
                Optional actions that the user can take for all these actions.  For example: "Continue, Stop".
                If not specified, by default there is a "Submit" action.

        Returns:
            str:
               The user's responses, mostly in the format of: `1. <response to question 1>; 2. <response to question 2>...`
        """
        if self.config.enable_interaction_without_callback:
            question_list = [
                f"<question_set><id>{q['id']}</id>\n<question>{q['question']}</question>\n<options>{q.get('options', '')}</options>\n<multiple_choice>{q.get('multiple_choice', False)}</multiple_choice></question_set>"
                for q in questions
            ]
            questions_str = f"<user_interaction>\n<prelude>{prelude}</prelude>\n" + "\n".join(question_list) + f"\n<actions>{actions}</actions>\n</user_interaction>"
            error_message = f"User interaction is required. \n{questions_str}"
            raise ShouldStop(error_message, retryable=False)
        try:
            assert self.callback is not None, "Callback must be provided for user interaction."

            question_list = [
                f"({q['id']}) {q['question']} Potential options: {q.get('options', 'None')}" for q in questions
            ]
            user_input = await self.callback("\n".join(question_list))
            return user_input
        except Exception as e:
            raise ToolExecutionError(f"Error during user interaction: {e}", retryable=True)

# No need to register for system tools as they will be initialized manually.
