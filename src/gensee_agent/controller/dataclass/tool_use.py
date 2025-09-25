from dataclasses import dataclass

from gensee_agent.settings import Settings

@dataclass
class ToolUse:
    """A dataclass representing a tool use action.

    Attributes:
    api_name (str): The name of the API to be called.  Example: "gensee.letter_counter.count_letters"
    params (dict): A dictionary of parameters to be passed to the API.
                   Example: {"param1": "value1", "param2": 2}
    """
    api_name: str
    params: dict

    def tool_name(self) -> str:
        return Settings.SEPARATOR.join(self.api_name.split(Settings.SEPARATOR)[:-1])

    def func_name(self) -> str:
        return self.api_name.split(Settings.SEPARATOR)[-1]