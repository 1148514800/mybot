from __future__ import annotations

import asyncio
import subprocess

from ..core.config import BrowserConfig
from ..storage.state import StateManager
from .base import Tool

_ACTIVE_SESSION = "default"


class PlaywrightCliTool(Tool):
    def _resolve_session(self, session: str = "") -> str:
        global _ACTIVE_SESSION
        return session.strip() or _ACTIVE_SESSION or "default"

    def _set_active_session(self, session: str) -> None:
        global _ACTIVE_SESSION
        _ACTIVE_SESSION = session.strip() or "default"

    def _session_prefix(self, session: str) -> list[str]:
        resolved = self._resolve_session(session)
        return ["playwright-cli", f"-s={resolved}"]

    async def _run_parts(self, parts: list[str]) -> str:
        try:
            proc = await asyncio.create_subprocess_exec(
                "cmd",
                "/c",
                *parts,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            out, err = await asyncio.wait_for(proc.communicate(), timeout=60)
            result = out.decode(errors="replace")
            if err:
                result += f"\nSTDERR:\n{err.decode(errors='replace')}"
            return (result or "(no output)")[:12000]
        except Exception as exc:
            return f"Error: {type(exc).__name__}: {exc}"


class BrowserOpenTool(PlaywrightCliTool):
    def __init__(
        self,
        browser_config: BrowserConfig | None = None,
        state_manager: StateManager | None = None,
    ):
        self._browser_config = browser_config or BrowserConfig()
        self._state_manager = state_manager

    def _default_session_for_url(self, url: str) -> str:
        normalized = url.strip().lower()
        for domain, session in self._browser_config.session_map.items():
            if domain in normalized:
                return session
        return "default"

    @property
    def name(self) -> str:
        return "browser_open"

    @property
    def description(self) -> str:
        return "Open a browser session with playwright-cli and optionally navigate to a URL."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to open", "default": ""},
                "headed": {
                    "type": ["boolean", "null"],
                    "description": "Open a visible browser window. Null means use config default.",
                    "default": None,
                },
                "browser": {
                    "type": "string",
                    "description": "Browser channel",
                    "enum": ["chrome", "msedge", "firefox", "webkit"],
                    "default": "chrome",
                },
                "session": {
                    "type": "string",
                    "description": "Browser session name. Leave empty to auto-select by URL.",
                    "default": "",
                },
                "persistent": {
                    "type": "boolean",
                    "description": "Use persistent browser profile",
                    "default": True,
                },
            },
        }

    async def execute(
        self,
        url: str = "",
        headed: bool | None = None,
        browser: str = "chrome",
        session: str = "",
        persistent: bool = True,
        **kwargs,
    ) -> str:
        resolved_url = url.strip()
        resolved_session = session.strip() or self._default_session_for_url(resolved_url)
        resolved_headed = self._browser_config.headed if headed is None else headed

        parts = self._session_prefix(resolved_session) + ["open"]
        if resolved_url:
            parts.append(resolved_url)
        if resolved_headed:
            parts.append("--headed")
        if browser.strip():
            parts.append(f"--browser={browser.strip()}")
        if persistent:
            parts.append("--persistent")

        result = await self._run_parts(parts)
        if not result.startswith("Error:"):
            self._set_active_session(resolved_session)
            if self._state_manager:
                self._state_manager.update_browser_state(
                    session_name=resolved_session,
                    last_opened_url=resolved_url or "about:blank",
                    headed=resolved_headed,
                )
        return result


class BrowserSnapshotTool(PlaywrightCliTool):
    @property
    def name(self) -> str:
        return "browser_snapshot"

    @property
    def description(self) -> str:
        return "Capture a snapshot of the current page or a specific element."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "session": {
                    "type": "string",
                    "description": "Browser session name",
                    "default": "",
                },
                "target": {
                    "type": "string",
                    "description": "Optional element ref or selector",
                    "default": "",
                },
                "depth": {
                    "type": "integer",
                    "description": "Optional snapshot depth",
                    "minimum": 1,
                },
                "filename": {
                    "type": "string",
                    "description": "Optional output filename",
                    "default": "",
                },
            },
        }

    async def execute(
        self,
        session: str = "",
        target: str = "",
        depth: int | None = None,
        filename: str = "",
        **kwargs,
    ) -> str:
        parts = self._session_prefix(session) + ["snapshot"]
        if filename.strip():
            parts.append(f"--filename={filename.strip()}")
        if depth is not None:
            parts.append(f"--depth={depth}")
        if target.strip():
            parts.append(target.strip())
        return await self._run_parts(parts)


class BrowserGotoTool(PlaywrightCliTool):
    def __init__(self, state_manager: StateManager | None = None):
        self._state_manager = state_manager

    @property
    def name(self) -> str:
        return "browser_goto"

    @property
    def description(self) -> str:
        return "Navigate the current page in an existing browser session to a URL."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to navigate to"},
                "session": {
                    "type": "string",
                    "description": "Browser session name",
                    "default": "",
                },
            },
            "required": ["url"],
        }

    async def execute(self, url: str, session: str = "", **kwargs) -> str:
        resolved_session = self._resolve_session(session)
        resolved_url = url.strip()
        parts = self._session_prefix(resolved_session) + ["goto", resolved_url]
        result = await self._run_parts(parts)
        if not result.startswith("Error:"):
            self._set_active_session(resolved_session)
            if self._state_manager:
                self._state_manager.update_browser_state(
                    session_name=resolved_session,
                    last_opened_url=resolved_url,
                )
        return result


class BrowserNewTabTool(PlaywrightCliTool):
    def __init__(self, state_manager: StateManager | None = None):
        self._state_manager = state_manager

    @property
    def name(self) -> str:
        return "browser_new_tab"

    @property
    def description(self) -> str:
        return "Open a new tab in an existing browser session."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to open in a new tab"},
                "session": {
                    "type": "string",
                    "description": "Browser session name",
                    "default": "",
                },
            },
            "required": ["url"],
        }

    async def execute(self, url: str, session: str = "", **kwargs) -> str:
        resolved_session = self._resolve_session(session)
        resolved_url = url.strip()
        script = f"window.open('{resolved_url}', '_blank')"
        parts = self._session_prefix(resolved_session) + ["eval", script]
        result = await self._run_parts(parts)
        if not result.startswith("Error:"):
            self._set_active_session(resolved_session)
            if self._state_manager:
                self._state_manager.update_browser_state(
                    session_name=resolved_session,
                    last_opened_url=resolved_url,
                )
        return result


class BrowserClickTool(PlaywrightCliTool):
    @property
    def name(self) -> str:
        return "browser_click"

    @property
    def description(self) -> str:
        return "Click or double-click an element by ref or selector."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "Element ref or selector"},
                "session": {
                    "type": "string",
                    "description": "Browser session name",
                    "default": "",
                },
                "double": {
                    "type": "boolean",
                    "description": "Use double click instead of single click",
                    "default": False,
                },
            },
            "required": ["target"],
        }

    async def execute(
        self,
        target: str,
        session: str = "",
        double: bool = False,
        **kwargs,
    ) -> str:
        command = "dblclick" if double else "click"
        parts = self._session_prefix(session) + [command, target.strip()]
        return await self._run_parts(parts)


class BrowserTypeTool(PlaywrightCliTool):
    @property
    def name(self) -> str:
        return "browser_type"

    @property
    def description(self) -> str:
        return "Type text or fill a target element in the browser."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to input"},
                "target": {
                    "type": "string",
                    "description": "Optional element ref or selector to fill",
                    "default": "",
                },
                "submit": {
                    "type": "boolean",
                    "description": "Submit after filling the target element",
                    "default": False,
                },
                "session": {
                    "type": "string",
                    "description": "Browser session name",
                    "default": "",
                },
            },
            "required": ["text"],
        }

    async def execute(
        self,
        text: str,
        target: str = "",
        submit: bool = False,
        session: str = "",
        **kwargs,
    ) -> str:
        if target.strip():
            parts = self._session_prefix(session) + ["fill", target.strip(), text]
            if submit:
                parts.append("--submit")
        else:
            parts = self._session_prefix(session) + ["type", text]
        return await self._run_parts(parts)


class BrowserPressTool(PlaywrightCliTool):
    @property
    def name(self) -> str:
        return "browser_press"

    @property
    def description(self) -> str:
        return "Press a keyboard key in the browser."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "Keyboard key such as Enter, Space, ArrowDown",
                },
                "session": {
                    "type": "string",
                    "description": "Browser session name",
                    "default": "",
                },
            },
            "required": ["key"],
        }

    async def execute(self, key: str, session: str = "", **kwargs) -> str:
        parts = self._session_prefix(session) + ["press", key.strip()]
        return await self._run_parts(parts)


class BrowserEvalTool(PlaywrightCliTool):
    @property
    def name(self) -> str:
        return "browser_eval"

    @property
    def description(self) -> str:
        return "Run JavaScript in the current page, optionally against a target element."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "script": {
                    "type": "string",
                    "description": "JavaScript expression or function to evaluate",
                },
                "target": {
                    "type": "string",
                    "description": "Optional element ref or selector",
                    "default": "",
                },
                "session": {
                    "type": "string",
                    "description": "Browser session name",
                    "default": "",
                },
            },
            "required": ["script"],
        }

    async def execute(
        self,
        script: str,
        target: str = "",
        session: str = "",
        **kwargs,
    ) -> str:
        parts = self._session_prefix(session) + ["eval", script]
        if target.strip():
            parts.append(target.strip())
        return await self._run_parts(parts)


class BrowserCloseTool(PlaywrightCliTool):
    @property
    def name(self) -> str:
        return "browser_close"

    @property
    def description(self) -> str:
        return "Close the current browser session."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "session": {
                    "type": "string",
                    "description": "Browser session name",
                    "default": "",
                },
            },
        }

    async def execute(self, session: str = "", **kwargs) -> str:
        parts = self._session_prefix(session) + ["close"]
        return await self._run_parts(parts)
