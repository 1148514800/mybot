from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Session:
    key: str
    summary: str = ""
    messages: list[dict] = field(default_factory=list)

    def get_history(self, max_messages: int = 50) -> list[dict]:
        recent = self.messages[-max_messages:]
        for index, message in enumerate(recent):
            if message.get("role") == "user":
                return recent[index:]
        return recent

    def update_summary(self, summary: str) -> None:
        self.summary = summary.strip()

    def build_prompt_history(self, max_recent_messages: int = 12) -> list[dict]:
        prompt_history: list[dict] = []
        if self.summary:
            prompt_history.append(
                {
                    "role": "system",
                    "content": f"# Session Summary\n{self.summary}",
                }
            )
        prompt_history.extend(self.get_history(max_messages=max_recent_messages))
        return prompt_history


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
            meta = {"type": "meta", "summary": session.summary}
            handle.write(json.dumps(meta, ensure_ascii=False) + "\n")
            for message in session.messages:
                handle.write(json.dumps(message, ensure_ascii=False) + "\n")

    def _load(self, key: str) -> Session | None:
        path = self.dir / f"{key.replace(':', '_')}.jsonl"
        if not path.exists():
            return None

        summary = ""
        messages: list[dict] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            if (
                isinstance(item, dict)
                and item.get("type") == "meta"
                and "summary" in item
            ):
                summary = str(item.get("summary", "")).strip()
                continue
            messages.append(item)

        return Session(key=key, summary=summary, messages=messages)
