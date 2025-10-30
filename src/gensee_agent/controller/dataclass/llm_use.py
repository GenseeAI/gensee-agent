from dataclasses import dataclass
from typing import Optional

@dataclass
class LLMUse:
    prompts: list[dict] # Example: [{"role": "user", "content": "What is the capital of France?"}]
    model_name: Optional[str] = None  # The name of the model to use.  None to use default.

    def append_prompt(self, role: str, content: str) -> None:
        self.prompts.append({"role": role, "content": content})

    def append_user_prompt(self, content: str, title: str) -> None:
        # User prompt does not have the title field in the content, so need to add it.
        new_content = f"<title>{title}</title>\n{content}"
        self.append_prompt("user", new_content)

    def append_assistant_prompt(self, content: str) -> None:
        # Assistant prompt already has the title field in the content when it returns, so no need to add it.
        self.append_prompt("assistant", content)

    def copy(self) -> "LLMUse":
        return LLMUse(prompts=self.prompts.copy(), model_name=self.model_name)