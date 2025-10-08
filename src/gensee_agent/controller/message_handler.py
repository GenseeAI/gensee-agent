import html
import json
import re
from typing import Optional
from defusedxml import ElementTree as ET
from xml.etree.ElementTree import ParseError
from xml.parsers.expat import ExpatError

from gensee_agent.controller.dataclass.tool_use import ToolUse
from gensee_agent.exceptions.gensee_exceptions import ToolParsingError

class MessageHandler:
    def __init__(self, config: dict):
        pass

    def extract_tool_use(self, message: str) -> Optional[ToolUse]:
        """
        Parse LLM response to extract tool use with JSON arguments.

        Expected format:
        <tool_use>
        <name>tool_name</name>
        <arguments>
        {
          "param": "value"
        }
        </arguments>
        </tool_use>

        Or without arguments:
        <tool_use>
        <name>tool_name</name>
        </tool_use>
        """
        # Pattern with optional arguments section
        pattern = r'<tool_use>\s*<name>(.*?)</name>(?:\s*<arguments>(.*?)</arguments>)?\s*</tool_use>'
        match = re.search(pattern, message, re.DOTALL | re.IGNORECASE)

        if not match:
            return None

        tool_name = match.group(1).strip()
        arguments_str = match.group(2)  # This will be None if no arguments section

        # Handle empty or missing arguments
        if arguments_str is None or not arguments_str.strip():
            arguments = {}
        else:
            try:
                arguments = json.loads(arguments_str.strip())
            except json.JSONDecodeError as e:
                # Log the error for debugging
                print(f"Failed to parse tool arguments as JSON: {e}")
                print(f"Raw arguments: {arguments_str}")
                return None

        return ToolUse(
            api_name=tool_name,
            params=arguments
        )

    def extract_title(self, message: str) -> Optional[str]:
        """
        Parse LLM response to extract title.

        Expected format:
        <title>Your Title Here</title>
        """
        pattern = r'<title>(.*?)</title>'
        match = re.search(pattern, message, re.DOTALL | re.IGNORECASE)

        if not match:
            return None

        title = match.group(1).strip()
        return title if title else None


    def handle_message(self, message_str: str) -> Optional[ToolUse]:
        """Parse the message string and extract tool use information.

        An example message string:
        <thinking>
            I will count occurrences of the letter "r" in the word "strawberry". The required parameters (letter and text) are known, so I\'ll call the letter-counting tool.
        </thinking>
        <tool_use>
        ...
        </tool_use>
        <results>
        ...
        </results>
        """
        return self.extract_tool_use(message_str)
