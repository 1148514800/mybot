from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..skills import SkillsLoader
from ..storage.memory import MemoryManager
from ..storage.state import StateManager


class ContextBuilder:
    bootstrap_files = ("AGENTS.md", "SOUL.md", "USER.md", "TOOLS.md")

    def __init__(
        self,
        workspace: Path,
        builtin_skills: Path | None = None,
        instructions_dir: Path | None = None,
        state_manager: StateManager | None = None,
        memory_manager: MemoryManager | None = None,
    ):
        self.workspace = workspace
        self.instructions_dir = instructions_dir or workspace / "instructions"
        self.skills = SkillsLoader(workspace, builtin_skills)
        self.state_manager = state_manager
        self.memory_manager = memory_manager

    def build_system_prompt(self) -> str:
        parts = [
            (
                "# Mini Agent\n\n"
                "你是一个运行在本地工作区中的 AI 助手。\n"
                f"当前运行目录：{self.workspace}\n"
                f"核心规则文件：{self.instructions_dir / 'SOUL.md'}\n"
                "优先基于当前文件、当前状态和工具执行结果回答，不要凭空猜测。\n"
                "当用户询问的是过往对话、之前做出的决定、之前提到的需求或其他历史上下文时，可以依赖对话记忆。\n"
                "但当用户是在要求你执行动作、核实当前状态、重新运行任务或再次调用工具时，不要把之前的 assistant 回复或之前的工具输出直接当作本轮结果。\n"
                "在这些情况下，应重新调用工具或重新检查当前状态后再回答。\n"
                "对于浏览器操作：如果当前已有可复用的浏览器 session，且用户只是要求打开另一个网站，优先使用 browser_goto，而不是再次调用 browser_open。\n"
                "如果用户明确要求新开一个页面、新开一个标签页，或要求保留当前页面再打开另一个网站，优先使用 browser_new_tab。\n"
                "只有在没有可用浏览器 session，或用户明确要求新启动浏览器时，才使用 browser_open。\n"
                "当用户明确要求“记住”“请记住”“帮我记住”某个长期有效的偏好、事实或约定时，可以调用 memory_write 将该信息写入长期记忆。\n"
                "当用户要求“记住”某些内容时，需要先判断保存目标：\n"
                "1. 如果内容属于个人偏好、项目事实、长期约定、可结构化复用的信息，优先写入 memory。\n"
                "2. 如果内容属于系统规则、agent 行为规范、长期执行原则，优先写入 SOUL.md 或用户明确指定的说明文件。\n"
                "3. 如果用户明确指定了某个文件，例如 SOUL.md、USER.md、README.md，则应修改该文件，而不是写入 memory。\n"
                "4. 不要把当前瞬时状态、一次性执行结果或临时网页内容写入长期记忆，也不要把这些内容写入 SOUL.md。"
            )
        ]

        for filename in self.bootstrap_files:
            path = self.instructions_dir / filename
            if path.exists():
                parts.append(f"## {filename}\n\n{path.read_text(encoding='utf-8')}")

        summary = self.skills.build_skills_summary()
        if summary:
            parts.append(
                "# Skills\n\n"
                "以下是当前可用的本地 skills。需要使用某个 skill 时，应先阅读对应的 SKILL.md，再按其中约定执行。\n"
                f"{summary}"
            )

        return "\n\n---\n\n".join(parts)

    def build_memory_summary(self) -> str:
        if not self.memory_manager:
            return ""
        return self.memory_manager.get_memory_summary()

    def build_runtime_state_summary(self) -> str:
        if not self.state_manager:
            return ""

        state = self.state_manager.get_runtime_state()
        browser = state.get("browser", {})
        if not isinstance(browser, dict):
            return ""

        active_session = str(browser.get("active_session", "")).strip()
        sessions = browser.get("sessions", {})
        if not active_session or not isinstance(sessions, dict):
            return ""

        active_state = sessions.get(active_session, {})
        lines = ["# Runtime State", f"- Active browser session: {active_session}"]

        if isinstance(active_state, dict):
            if active_state.get("last_opened_url"):
                lines.append(f"- Current session URL: {active_state['last_opened_url']}")
            if "headed" in active_state:
                lines.append(f"- Current session headed mode: {active_state['headed']}")

        known_sessions: list[str] = []
        for session_name, session_state in sessions.items():
            if not isinstance(session_state, dict):
                continue
            url = str(session_state.get("last_opened_url", "")).strip()
            if not url:
                continue
            known_sessions.append(f"  - {session_name}: {url}")

        if known_sessions:
            lines.append("- Known browser sessions:")
            lines.extend(known_sessions)

        return "\n".join(lines)

    def build_messages(self, history: list[dict], user_message: str) -> list[dict]:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        messages = [{"role": "system", "content": self.build_system_prompt()}]

        memory_summary = self.build_memory_summary()
        if memory_summary:
            messages.append({"role": "system", "content": memory_summary})

        runtime_state = self.build_runtime_state_summary()
        if runtime_state:
            messages.append({"role": "system", "content": runtime_state})

        messages.extend(history)
        messages.append({"role": "user", "content": f"[Time: {now}]\n\n{user_message}"})
        return messages
