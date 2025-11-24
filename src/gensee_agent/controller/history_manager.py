import traceback
import aiofiles
from datetime import datetime
import json
import os
from typing import Any, Optional
from dataclasses import asdict, is_dataclass
from redis.asyncio import Redis, RedisCluster

from gensee_agent.utils.configs import BaseConfig, register_configs
from gensee_agent.utils.logging import configure_logger
from gensee_agent.controller.dataclass.llm_use import LLMUse

logger = configure_logger(__name__)

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

    def __init__(self, config: dict, session_id: Optional[str] = None, redis_client: Optional[Redis | RedisCluster] = None):
        self.config = self.Config.from_dict(config)
        if self.config.history_dump_path is not None:
            # Add the current timestamp to the dump path to avoid overwriting
            base, ext = os.path.splitext(self.config.history_dump_path)
            self.dump_path = f"{base}_{datetime.now().strftime('%Y%m%d-%H%M%S')}{ext}"
        else:
            self.dump_path = None

        self.redis_client = redis_client
        self.session_id = session_id
        self.history = []

    async def add_entry(self, name: str, title: str, entry: Any):
        history_entry = {
            "name": name,
            "title": title,
            "entry": entry
        }
        self.history.append(history_entry)
        if self.dump_path is not None:
            async with aiofiles.open(self.dump_path, "w") as f:
                await f.write(json.dumps(self.history, indent=2, cls=CustomJSONEncoder))
        if self.redis_client is not None and self.session_id is not None:
            # Only need to store the last entry for "llm_use" type in Redis
            if name == "llm_use":
                await self.redis_client.set(self.session_id, json.dumps(history_entry, cls=CustomJSONEncoder, separators=(',', ':'), indent=None) + "\n")

    async def get_history(self) -> Optional[dict]:
        """
        Return value: dict of "name", "title", and "entry".  Entry will be a plain dict, not LLMUse class.
        """
        if self.redis_client is None or self.session_id is None:
            return None
        raise NotImplementedError("get_history is deprecated and not implemented.  Currently it doesn't handle model_name properly.  Needs to reimplement.")
        # data = await self.redis_client.get(self.session_id)
        # if data is None:
        #     return None
        # history_entry = json.loads(data)
        # logger.info(f"Loaded history for session_id {self.session_id}")
        # return history_entry

    async def read_history(self) -> bool:
        """
        Returns True if history exists and is loaded, False otherwise.
        """
        history_entry = await self.get_history()
        if history_entry is None:
            return False
        raise NotImplementedError("read_history is deprecated and not implemented.  Currently it doesn't handle model_name properly.  Needs to reimplement.")
        # if history_entry is not None:
        #     history_entry["entry"] = LLMUse(**history_entry["entry"])
        #     self.history = [history_entry]
        #     return True
        # return False

    async def set_history(self, history: dict, model_name: Optional[str] = None):
        """
        history: dict of "name", "title", and "entry".  Entry will be a plain dict, not LLMUse class.
        """
        if self.redis_client is None or self.session_id is None:
            return
        raise NotImplementedError("set_history is deprecated and not implemented.  Currently it doesn't handle model_name properly.  Needs to reimplement.")
        # if await self.get_history() is not None:
        #     # Don't overwrite existing history
        #     return
        # if self.redis_client is not None and self.session_id is not None:
        #     response = await self.redis_client.set(self.session_id, json.dumps(history, separators=(',', ':'), indent=None) + "\n")
        #     if not response:
        #         logger.error(f"Failed to set history for session_id {self.session_id}")
        #     else:
        #         logger.info(f"Set history for session_id {self.session_id}")
        # history["entry"] = LLMUse(**history["entry"], model_name=model_name)
        # self.history = [history]

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
