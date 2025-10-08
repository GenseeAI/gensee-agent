from dataclasses import dataclass
from typing import Optional, TypeAlias

@dataclass
class SingleLLMResponse:
    finish_reason: str
    title: str
    content: Optional[str]
    partial: bool = False


LLMResponses: TypeAlias = list[SingleLLMResponse]