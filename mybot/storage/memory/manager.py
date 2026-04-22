from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


class MemoryManager:
    def __init__(self, workspace: Path):
        self.dir = workspace / "memory"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "memory.json"

    def _default_memory(self) -> dict:
        return {
            "user_preferences": {},
            "project_facts": {},
            "browser_preferences": {"default_sessions": {}},
            "custom_facts": [],
        }

    def _normalize_memory(self, data: dict | None) -> dict:
        memory = self._default_memory()
        if isinstance(data, dict):
            memory.update({k: v for k, v in data.items() if isinstance(k, str)})

        if not isinstance(memory.get("user_preferences"), dict):
            memory["user_preferences"] = {}
        if not isinstance(memory.get("project_facts"), dict):
            memory["project_facts"] = {}
        if not isinstance(memory.get("browser_preferences"), dict):
            memory["browser_preferences"] = {"default_sessions": {}}
        if not isinstance(memory["browser_preferences"].get("default_sessions"), dict):
            memory["browser_preferences"]["default_sessions"] = {}
        if not isinstance(memory.get("custom_facts"), list):
            memory["custom_facts"] = []

        normalized_custom_facts: list[dict] = []
        for item in memory["custom_facts"]:
            if not isinstance(item, dict):
                continue
            key = str(item.get("key", "")).strip()
            if not key:
                continue
            normalized_custom_facts.append(
                {
                    "key": key,
                    "value": item.get("value"),
                    "category": str(item.get("category", "general")).strip() or "general",
                    "source": str(item.get("source", "user")).strip() or "user",
                    "updated_at": str(item.get("updated_at", "")).strip(),
                }
            )
        memory["custom_facts"] = normalized_custom_facts
        return memory

    def load(self) -> dict:
        if not self.path.exists():
            return self._default_memory()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return self._default_memory()
        return self._normalize_memory(data if isinstance(data, dict) else {})

    def save(self, memory: dict) -> None:
        normalized = self._normalize_memory(memory)
        self.path.write_text(
            json.dumps(normalized, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def get_memory(self) -> dict:
        return self.load()

    def _now(self) -> str:
        return datetime.now().isoformat()

    def get_memory_summary(self) -> str:
        memory = self.get_memory()
        lines: list[str] = ["# Memory"]

        user_preferences = memory.get("user_preferences", {})
        project_facts = memory.get("project_facts", {})
        browser_preferences = memory.get("browser_preferences", {})
        default_sessions = browser_preferences.get("default_sessions", {})
        custom_facts = memory.get("custom_facts", [])

        if user_preferences.get("language"):
            lines.append(f"- Preferred language: {user_preferences['language']}")
        if user_preferences.get("preferred_browser"):
            lines.append(f"- Preferred browser: {user_preferences['preferred_browser']}")

        if project_facts.get("config_path"):
            lines.append(f"- Config path: {project_facts['config_path']}")
        if project_facts.get("model_provider"):
            lines.append(f"- Model provider: {project_facts['model_provider']}")

        for domain, session in default_sessions.items():
            if domain and session:
                lines.append(f"- Default browser session for {domain}: {session}")

        for item in custom_facts:
            key = item.get("key")
            value = item.get("value")
            category = item.get("category", "general")
            if key and value not in (None, ""):
                lines.append(f"- [{category}] {key}: {value}")

        return "" if len(lines) == 1 else "\n".join(lines)

    def set_user_preference(self, key: str, value) -> None:
        memory = self.get_memory()
        memory.setdefault("user_preferences", {})[key] = value
        self.save(memory)

    def set_project_fact(self, key: str, value) -> None:
        memory = self.get_memory()
        memory.setdefault("project_facts", {})[key] = value
        self.save(memory)

    def set_browser_session(self, domain: str, session: str) -> None:
        memory = self.get_memory()
        browser_preferences = memory.setdefault("browser_preferences", {})
        default_sessions = browser_preferences.setdefault("default_sessions", {})
        default_sessions[domain] = session
        self.save(memory)

    def list_custom_facts(self) -> list[dict]:
        memory = self.get_memory()
        return list(memory.get("custom_facts", []))

    def get_custom_fact(self, key: str):
        lookup = key.strip()
        if not lookup:
            return None
        for item in self.list_custom_facts():
            if item.get("key") == lookup:
                return item
        return None

    def set_custom_fact(
        self,
        key: str,
        value,
        category: str = "general",
        source: str = "user",
    ) -> None:
        lookup = key.strip()
        if not lookup:
            raise ValueError("key is required")

        memory = self.get_memory()
        custom_facts = memory.setdefault("custom_facts", [])
        updated = False
        for item in custom_facts:
            if item.get("key") == lookup:
                item["value"] = value
                item["category"] = category or "general"
                item["source"] = source or "user"
                item["updated_at"] = self._now()
                updated = True
                break

        if not updated:
            custom_facts.append(
                {
                    "key": lookup,
                    "value": value,
                    "category": category or "general",
                    "source": source or "user",
                    "updated_at": self._now(),
                }
            )

        self.save(memory)

    def delete_custom_fact(self, key: str) -> bool:
        lookup = key.strip()
        if not lookup:
            return False

        memory = self.get_memory()
        custom_facts = memory.setdefault("custom_facts", [])
        new_items = [item for item in custom_facts if item.get("key") != lookup]
        if len(new_items) == len(custom_facts):
            return False
        memory["custom_facts"] = new_items
        self.save(memory)
        return True
