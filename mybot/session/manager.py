from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Session:
    key: str
    messages: list[dict] = field(default_factory=list)

    def get_history(self, max_messages: int = 50) -> list[dict]:
        recent = self.messages[-max_messages:]
        for index, message in enumerate(recent):
            if message.get("role") == "user":
                return recent[index:]
        return recent


class SessionManager:
    def __init__(self, workspace: Path):
        self.dir = workspace / "sessions"
        self.dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, Session] = {}

    def get_or_create(self, key: str) -> Session:
        if key in self._cache:
            return self._cache[key]
        session = self._load(key) or Session(key=key)
        self._cache[key] = session
        return session

    def save(self, session: Session) -> None:
        path = self.dir / f"{session.key.replace(':', '_')}.jsonl"
        with open(path, "w", encoding="utf-8") as handle:
            for message in session.messages:
                handle.write(json.dumps(message, ensure_ascii=False) + "\n")

    def _load(self, key: str) -> Session | None:
        path = self.dir / f"{key.replace(':', '_')}.jsonl"
        if not path.exists():
            return None
        messages = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        return Session(key=key, messages=messages)
