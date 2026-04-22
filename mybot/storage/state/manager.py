from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


class StateManager:
    def __init__(self, workspace: Path):
        self.dir = workspace / "state"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "runtime_state.json"

    def _default_state(self) -> dict:
        return {
            "browser": {
                "active_session": "default",
                "sessions": {},
            }
        }

    def _normalize_state(self, data: dict | None) -> dict:
        state = self._default_state()
        if isinstance(data, dict):
            state.update({k: v for k, v in data.items() if isinstance(k, str)})

        browser = state.get("browser")
        if not isinstance(browser, dict):
            browser = {}
        state["browser"] = browser

        active_session = str(browser.get("active_session", "default")).strip() or "default"
        browser["active_session"] = active_session

        sessions = browser.get("sessions")
        if not isinstance(sessions, dict):
            sessions = {}

        legacy_url = browser.get("last_opened_url")
        legacy_headed = browser.get("headed")
        if active_session not in sessions and (
            legacy_url is not None or legacy_headed is not None
        ):
            sessions[active_session] = {}
            if legacy_url is not None:
                sessions[active_session]["last_opened_url"] = legacy_url
            if legacy_headed is not None:
                sessions[active_session]["headed"] = legacy_headed

        normalized_sessions: dict[str, dict] = {}
        for session_name, session_state in sessions.items():
            name = str(session_name).strip()
            if not name or not isinstance(session_state, dict):
                continue
            normalized_sessions[name] = {
                "last_opened_url": str(
                    session_state.get("last_opened_url", "")
                ).strip(),
                "headed": bool(session_state.get("headed", False)),
                "updated_at": str(session_state.get("updated_at", "")).strip(),
            }

        browser["sessions"] = normalized_sessions
        browser.pop("last_opened_url", None)
        browser.pop("headed", None)
        return state

    def load(self) -> dict:
        if not self.path.exists():
            return self._default_state()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return self._default_state()
        return self._normalize_state(data if isinstance(data, dict) else {})

    def save(self, state: dict) -> None:
        normalized = self._normalize_state(state)
        self.path.write_text(
            json.dumps(normalized, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def get_runtime_state(self) -> dict:
        return self.load()

    def update_browser_state(
        self,
        session_name: str,
        last_opened_url: str | None = None,
        headed: bool | None = None,
    ) -> None:
        resolved_session = session_name.strip() or "default"

        state = self.load()
        browser = state.setdefault("browser", {})
        browser["active_session"] = resolved_session

        sessions = browser.setdefault("sessions", {})
        session_state = sessions.setdefault(resolved_session, {})

        if last_opened_url is not None:
            session_state["last_opened_url"] = last_opened_url
        if headed is not None:
            session_state["headed"] = headed
        session_state["updated_at"] = datetime.now().isoformat()

        self.save(state)
