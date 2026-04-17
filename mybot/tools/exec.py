from __future__ import annotations

import asyncio

from .base import Tool


class ExecTool(Tool):
    @property
    def name(self) -> str:
        return "exec"

    @property
    def description(self) -> str:
        return "Execute a shell command."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command"},
            },
            "required": ["command"],
        }

    async def execute(self, command: str, **kwargs) -> str:
        for bad in ["rm -rf", "mkfs", "dd if=", "shutdown"]:
            if bad in command.lower():
                return f"Error: Blocked ({bad})"
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            out, err = await asyncio.wait_for(proc.communicate(), timeout=30)
            result = out.decode(errors="replace")
            if err:
                result += f"\nSTDERR:\n{err.decode(errors='replace')}"
            return (result or "(no output)")[:10000]
        except Exception as exc:
            return f"Error: {exc}"
