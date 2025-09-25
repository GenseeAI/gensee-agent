from dataclasses import dataclass
from typing import Optional

@dataclass
class LLMUse:
    prompts: list[dict] # Example: [{"role": "user", "content": "What is the capital of France?"}]
    model_name: Optional[str] = None  # The name of the model to use.  None to use default.

    def append_prompt(self, role: str, content: str) -> None:
        self.prompts.append({"role": role, "content": content})

    def append_user_prompt(self, content: str) -> None:
        self.append_prompt("user", content)

    def append_assistant_prompt(self, content: str) -> None:
        self.append_prompt("assistant", content)

    def copy(self) -> "LLMUse":
        return LLMUse(prompts=self.prompts.copy(), model_name=self.model_name)