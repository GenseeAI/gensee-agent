from typing import Optional
from xml.etree.ElementTree import ParseError
from defusedxml import ElementTree as ET
from xml.parsers.expat import ExpatError

from gensee_agent.controller.dataclass.tool_use import ToolUse
from gensee_agent.exceptions.gensee_exceptions import ToolParsingError

class MessageHandler:
    def __init__(self, config: dict):
        pass

    def handle_message(self, message_str: str) -> Optional[ToolUse]:
        """Parse the message string and extract tool use information.

        An example message string:
        <thinking>
            I will count occurrences of the letter "r" in the word "strawberry". The required parameters (letter and text) are known, so I\'ll call the letter-counting tool.
        </thinking>
        <gensee.letter_counter.count_letters>
            <letter>r</letter>
            <text>strawberry</text>
        </gensee.letter_counter.count_letters>
        """

        # Parse the XML message
        xml = "<root>" + message_str + "</root>"  # Wrap in a root element
        try:
            root = ET.fromstring(xml)
        except (ParseError, ExpatError) as e:
            print(f"Error parsing XML: {e}")
            raise ToolParsingError(f"Error parsing XML: {e}", retryable=False)

        tool_use = None
        for elem in root:
            if elem.tag == "thinking":
                continue
            api_name = elem.tag
            argmap = {child.tag: child.text for child in elem}
            if tool_use is not None:
                raise ValueError("Multiple tool use tags found in the message.")
            tool_use = ToolUse(api_name=api_name, params=argmap)
        return tool_use
