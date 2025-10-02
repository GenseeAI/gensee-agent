import html
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

    # Regex for sloppy inputs
    _BARE_AMP = re.compile(r'&(?!#\d+;|#x[0-9A-Fa-f]+;|[A-Za-z][A-Za-z0-9._-]*;)')
    _BAD_CTRL = re.compile(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]')
    _STRAY_LT = re.compile(r'<(?!(?:\?|!|/?[A-Za-z_]))')

    def sanitize_xml(self, xml_text: str, escape_lt=False) -> str:
        """Escape invalid chars to make XML parseable."""
        if not isinstance(xml_text, str):
            xml_text = xml_text.decode("utf-8", errors="replace")

        xml_text = self._BAD_CTRL.sub("", xml_text)
        xml_text = self._BARE_AMP.sub("&amp;", xml_text)

        if escape_lt:
            xml_text = self._STRAY_LT.sub("&lt;", xml_text)

        return xml_text

    def get_original_text(self, text: Optional[str]) -> Optional[str]:
        """
        Extract text from an XML element, but unescape entities
        (so you get back the original sloppy content).
        """
        if text is None:
            return None
        return html.unescape(text)

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
        xml = "<root>" + self.sanitize_xml(message_str, escape_lt=True) + "</root>"  # Wrap in a root element
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
            argmap = {child.tag: self.get_original_text(child.text) for child in elem}
            if tool_use is not None:
                raise ValueError("Multiple tool use tags found in the message.")
            tool_use = ToolUse(api_name=api_name, params=argmap)
        return tool_use
