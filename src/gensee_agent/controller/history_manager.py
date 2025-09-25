from typing import Any


class HistoryManager:
    def __init__(self):
        self.history = []

    def add_entry(self, name: str, entry: Any):
        self.history.append({
            "name": name,
            "entry": entry
        })

    def get_last_entry_of_type(self, name: str) -> Any:
        for record in reversed(self.history):
            if record["name"] == name:
                return record["entry"]
        return None

    def entry_count(self) -> int:
        return len(self.history)
