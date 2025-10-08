from dataclasses import dataclass, field
import random
import string

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
    call_id: str = field(default_factory=lambda: ToolUse.generate_call_id())

    @classmethod
    def generate_call_id(cls) -> str:
        chars = ''.join(c for c in string.ascii_uppercase + string.digits
                   if c not in 'IL10O')
        random_id = ''.join(random.choices(chars, k=4))
        return random_id

    def tool_name(self) -> str:
        return Settings.SEPARATOR.join(self.api_name.split(Settings.SEPARATOR)[:-1])

    def func_name(self) -> str:
        return self.api_name.split(Settings.SEPARATOR)[-1]

    def title(self) -> str:
        return f"Tool: {self.api_name} ID: {self.call_id}"
