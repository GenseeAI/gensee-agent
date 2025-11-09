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
        self.append_prompt("user", self.add_title(content, title))

    def append_assistant_prompt(self, content: str) -> None:
        # Assistant prompt already has the title field in the content when it returns, so no need to add it.
        self.append_prompt("assistant", content)

    def set_or_update_system_prompt(self, role: str, content: str) -> None:
        if role != "system":
            raise ValueError("Role must be 'system' to set or update system prompt.")
        for prompt in self.prompts:
            if prompt["role"] == "system":
                prompt["content"] = content
                return
        self.prompts.insert(0, {"role": "system", "content": content})

    def copy(self) -> "LLMUse":
        return LLMUse(prompts=self.prompts.copy(), model_name=self.model_name)

    def has_title(self, content: str) -> bool:
        # Check if the title field exists in the content
        return "<title>" in content and "</title>" in content

    def add_title(self, content: str, title: str) -> str:
        if self.has_title(content):
            return content
        return f"<title>{title}</title>\n{content}"