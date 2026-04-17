from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..skills import SkillsLoader


class ContextBuilder:
    bootstrap_files = ("AGENTS.md", "SOUL.md", "USER.md", "TOOLS.md")

    def __init__(self, workspace: Path, builtin_skills: Path | None = None):
        self.workspace = workspace
        self.skills = SkillsLoader(workspace, builtin_skills)

    def build_system_prompt(self) -> str:
        parts = [
            (
                "# Mini Agent\n\n"
                "你是一个有帮助的 AI 助手。\n"
                f"工作区: {self.workspace}\n"
                f"自我设定文件: {self.workspace / 'SOUL.md'}\n"
                "当用户要求你修改名字、身份、说话风格或长期人格设定时，更新 SOUL.md。"
            )
        ]
        for filename in self.bootstrap_files:
            path = self.workspace / filename
            if path.exists():
                parts.append(f"## {filename}\n\n{path.read_text(encoding='utf-8')}")

        summary = self.skills.build_skills_summary()
        if summary:
            parts.append(
                "# Skills\n\n"
                "以下技能扩展了你的能力。需要时用 read_file 读取 SKILL.md 获取详情。\n"
                f"{summary}"
            )

        return "\n\n---\n\n".join(parts)

    def build_messages(self, history: list[dict], user_message: str) -> list[dict]:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        return [
            {"role": "system", "content": self.build_system_prompt()},
            *history,
            {"role": "user", "content": f"[Time: {now}]\n\n{user_message}"},
        ]
