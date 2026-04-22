from __future__ import annotations

from pathlib import Path

from ..core.config import BrowserConfig
from ..storage.memory import MemoryManager
from ..storage.state import StateManager
from .base import Tool
from .browser import (
    BrowserClickTool,
    BrowserCloseTool,
    BrowserEvalTool,
    BrowserGotoTool,
    BrowserNewTabTool,
    BrowserOpenTool,
    BrowserPressTool,
    BrowserSnapshotTool,
    BrowserTypeTool,
)
from .exec import ExecTool
from .file_tools import ReadFileTool, WriteFileTool
from .memory import MemoryReadTool, MemoryWriteTool


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get_definitions(self) -> list[dict]:
        return [tool.to_schema() for tool in self._tools.values()]

    async def execute(self, name: str, params: dict) -> str:
        tool = self._tools.get(name)
        if not tool:
            return f"Error: Unknown tool '{name}'"
        try:
            return await tool.execute(**params)
        except Exception as exc:
            return f"Error: {exc}"


def build_default_tool_registry(
    workspace: Path,
    browser_config: BrowserConfig | None = None,
    state_manager: StateManager | None = None,
    memory_manager: MemoryManager | None = None,
) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(ExecTool())
    registry.register(
        BrowserOpenTool(
            browser_config=browser_config,
            state_manager=state_manager,
        )
    )
    registry.register(BrowserSnapshotTool())
    registry.register(BrowserGotoTool(state_manager=state_manager))
    registry.register(BrowserNewTabTool(state_manager=state_manager))
    registry.register(BrowserClickTool())
    registry.register(BrowserTypeTool())
    registry.register(BrowserPressTool())
    registry.register(BrowserEvalTool())
    registry.register(BrowserCloseTool())
    if memory_manager:
        registry.register(MemoryWriteTool(memory_manager))
        registry.register(MemoryReadTool(memory_manager))
    registry.register(ReadFileTool(workspace))
    registry.register(WriteFileTool(workspace))
    return registry
