import aiofiles
from datetime import datetime
import json
import os
from typing import Any, Optional
from dataclasses import asdict, is_dataclass
import redis.asyncio as redis

from gensee_agent.configs.configs import BaseConfig, register_configs
from gensee_agent.controller.dataclass.llm_use import LLMUse

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
        redis_url: Optional[str] = None  # Redis URL for storing history, if needed.

    def __init__(self, config: dict, session_id: Optional[str] = None):
        self.config = self.Config.from_dict(config)
        if self.config.history_dump_path is not None:
            # Add the current timestamp to the dump path to avoid overwriting
            base, ext = os.path.splitext(self.config.history_dump_path)
            self.dump_path = f"{base}_{datetime.now().strftime('%Y%m%d-%H%M%S')}{ext}"
        else:
            self.dump_path = None

        if self.config.redis_url is not None:
            self.redis_client = redis.from_url(self.config.redis_url)
            assert session_id is not None, "session_id must be provided if redis_url is set."
        else:
            self.redis_client = None
        self.session_id = session_id
        self.history = []

    async def add_entry(self, name: str, title: str, entry: Any):
        entry = {
            "name": name,
            "title": title,
            "entry": entry
        }
        self.history.append(entry)
        if self.dump_path is not None:
            async with aiofiles.open(self.dump_path, "w") as f:
                await f.write(json.dumps(self.history, indent=2, cls=CustomJSONEncoder))
        if self.redis_client is not None and self.session_id is not None:
            # Only need to store the last entry for "llm_use" type in Redis
            if name == "llm_use":
                await self.redis_client.set(self.session_id, json.dumps(entry, cls=CustomJSONEncoder, separators=(',', ':'), indent=None) + "\n")

    async def read_history(self) -> bool:
        if self.redis_client is None or self.session_id is None:
            return False
        data = await self.redis_client.get(self.session_id)
        if data is None:
            return False
        entry = json.loads(data)
        entry["entry"] = LLMUse(**entry["entry"])
        self.history = [entry]
        return True

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
