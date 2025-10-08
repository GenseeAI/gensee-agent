from datetime import datetime
import json
import os
from typing import Any, Optional
from dataclasses import asdict, is_dataclass

from gensee_agent.configs.configs import BaseConfig, register_configs

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, o):
        # Handle dataclasses
        if is_dataclass(o) and not isinstance(o, type):
            return asdict(o)
        # Handle objects with __dict__ (most custom classes)
        if hasattr(o, '__dict__'):
            return o.__dict__
        # Handle other types by converting to string
        return str(o)

class HistoryManager:

    @register_configs("history_manager")
    class Config(BaseConfig):
        history_dump_path: Optional[str] = None  # Path to dump history, if needed.

    def __init__(self, config: dict):
        self.config = self.Config.from_dict(config)
        if self.config.history_dump_path is not None:
            # Add the current timestamp to the dump path to avoid overwriting
            base, ext = os.path.splitext(self.config.history_dump_path)
            self.dump_path = f"{base}_{datetime.now().strftime('%Y%m%d-%H%M%S')}{ext}"
        else:
            self.dump_path = None

        self.history = []

    def add_entry(self, name: str, title: str, entry: Any):
        self.history.append({
            "name": name,
            "title": title,
            "entry": entry
        })
        if self.dump_path is not None:
            with open(self.dump_path, "w") as f:
                json.dump(self.history, f, indent=2, cls=CustomJSONEncoder)

    def get_last_entry_of_type(self, name: str) -> Any:
        for record in reversed(self.history):
            if record["name"] == name:
                return record["entry"]
        return None

    def get_last_entry_title(self) -> str:
        if not self.history:
            return "[No History]"
        return self.history[-1]["title"]

    def entry_count(self) -> int:
        return len(self.history)
