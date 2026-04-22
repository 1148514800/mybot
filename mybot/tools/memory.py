from __future__ import annotations

import json

from ..storage.memory import MemoryManager
from .base import Tool


class MemoryWriteTool(Tool):
    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager

    @property
    def name(self) -> str:
        return "memory_write"

    @property
    def description(self) -> str:
        return "Write or update a long-term memory item."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Memory key"},
                "value": {"description": "Memory value"},
                "category": {
                    "type": "string",
                    "description": "Memory category such as preference, project, general",
                    "default": "general",
                },
                "source": {
                    "type": "string",
                    "description": "Memory source such as user or system",
                    "default": "user",
                },
            },
            "required": ["key", "value"],
        }

    async def execute(
        self,
        key: str,
        value,
        category: str = "general",
        source: str = "user",
        **kwargs,
    ) -> str:
        self.memory_manager.set_custom_fact(
            key=key,
            value=value,
            category=category,
            source=source,
        )
        item = self.memory_manager.get_custom_fact(key)
        return json.dumps(item or {}, ensure_ascii=False)


class MemoryReadTool(Tool):
    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager

    @property
    def name(self) -> str:
        return "memory_read"

    @property
    def description(self) -> str:
        return "Read long-term memory items by key, or return all custom facts if no key is given."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "Optional memory key to read",
                    "default": "",
                }
            },
        }

    async def execute(self, key: str = "", **kwargs) -> str:
        lookup = key.strip()
        if lookup:
            item = self.memory_manager.get_custom_fact(lookup)
            return json.dumps(item or {}, ensure_ascii=False)
        return json.dumps(self.memory_manager.list_custom_facts(), ensure_ascii=False)
