from __future__ import annotations

import asyncio
import json
from datetime import datetime

from openai import OpenAI

from ..core.config import GatewayConfig
from ..messaging import MessageBus, OutboundMessage
from ..storage.session import SessionManager
from ..tools import ToolRegistry
from .context import ContextBuilder


class AgentLoop:
    def __init__(
        self,
        client: OpenAI,
        config: GatewayConfig,
        bus: MessageBus,
        tools: ToolRegistry,
        context: ContextBuilder,
        sessions: SessionManager,
    ):
        self.client = client
        self.config = config
        self.bus = bus
        self.tools = tools
        self.context = context
        self.sessions = sessions

    def _trace(self, message: str) -> None:
        if self.config.show_internal_process:
            print(f"[trace] {message}")

    def _is_rate_limit_error(self, exc: Exception) -> bool:
        text = f"{type(exc).__name__}: {exc}"
        return (
            "RateLimitError" in text
            or "429" in text
            or "TPM limit reached" in text
        )

    def _build_session_summary(self, session) -> str:
        recent = session.messages[-20:]
        user_messages = [
            str(message.get("content", "")).strip()
            for message in recent
            if message.get("role") == "user" and str(message.get("content", "")).strip()
        ]
        assistant_messages = [
            str(message.get("content", "")).strip()
            for message in recent
            if message.get("role") == "assistant" and str(message.get("content", "")).strip()
        ]

        summary_parts: list[str] = []
        if user_messages:
            summary_parts.append(f"Recent user focus: {user_messages[-1][:200]}")
        if len(user_messages) >= 2:
            summary_parts.append(f"Previous user request: {user_messages[-2][:200]}")
        if assistant_messages:
            summary_parts.append(f"Recent assistant reply: {assistant_messages[-1][:200]}")
        return "\n".join(summary_parts).strip()

    async def run(self):
        while True:
            try:
                message = await asyncio.wait_for(self.bus.consume_inbound(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            session = self.sessions.get_or_create(message.session_key)
            history = session.build_prompt_history(max_recent_messages=12)
            messages = self.context.build_messages(history, message.content)
            reply = await self._react_loop(messages)

            session.messages.append(
                {
                    "role": "user",
                    "content": message.content,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            session.messages.append(
                {
                    "role": "assistant",
                    "content": reply,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            session.update_summary(self._build_session_summary(session))
            self.sessions.save(session)

            await self.bus.publish_outbound(
                OutboundMessage(channel=message.channel, chat_id=message.chat_id, content=reply)
            )

    async def _react_loop(self, messages: list[dict]) -> str:
        final_parts: list[str] = []
        rate_limit_retries = 0
        for step in range(self.config.max_react_steps):
            self._trace(f"model step={step + 1}")
            try:
                response = self.client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    tools=self.tools.get_definitions() or None,
                    temperature=0.1,
                    max_tokens=self.config.max_completion_tokens,
                )
            except Exception as exc:
                if (
                    self._is_rate_limit_error(exc)
                    and rate_limit_retries < self.config.rate_limit_retries
                ):
                    rate_limit_retries += 1
                    self._trace(
                        "rate limited, waiting 60s before retry "
                        f"{rate_limit_retries}/{self.config.rate_limit_retries}"
                    )
                    await asyncio.sleep(60)
                    continue
                return f"调用模型时出错: {type(exc).__name__}: {exc}"

            choice = response.choices[0]
            message = choice.message
            finish_reason = choice.finish_reason

            if finish_reason == "length" and message.content:
                final_parts.append(message.content)
                messages.append({"role": "assistant", "content": message.content})
                messages.append(
                    {
                        "role": "user",
                        "content": "Continue from exactly where you stopped. Do not repeat prior text.",
                    }
                )
                continue

            if not message.tool_calls:
                if message.content:
                    final_parts.append(message.content)
                return "".join(final_parts).strip()

            messages.append(
                {
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [
                        {
                            "id": tool_call.id,
                            "type": "function",
                            "function": {
                                "name": tool_call.function.name,
                                "arguments": tool_call.function.arguments,
                            },
                        }
                        for tool_call in message.tool_calls
                    ],
                }
            )

            for tool_call in message.tool_calls:
                args = json.loads(tool_call.function.arguments)
                self._trace(
                    f"tool call name={tool_call.function.name} args={tool_call.function.arguments}"
                )
                result = await self.tools.execute(tool_call.function.name, args)
                preview = result[:300].replace("\n", " ")
                self._trace(f"tool result name={tool_call.function.name} result={preview}")
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    }
                )

        return "Max iterations reached."
