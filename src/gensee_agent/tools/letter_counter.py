from gensee_agent.tools.base import BaseTool, register_tool, public_api
from gensee_agent.settings import Settings

class LetterCounter(BaseTool):

    def __init__(self, tool_name: str, config: dict):
        super().__init__(tool_name, config)

    @public_api
    def count_letters(self, letter: str, text: str) -> int:
        """Count occurrences of a specific letter in the given text.

        Args:
            letter (str): The letter to count.
            text (str): The text in which to count the letter.

        Returns:
            int: The number of occurrences of the letter in the text.
        """
        return text.lower().count(letter.lower())

register_tool(f"gensee{Settings.SEPARATOR}letter_counter", LetterCounter)