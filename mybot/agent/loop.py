from __future__ import annotations

import asyncio
import json
from datetime import datetime

from openai import OpenAI

from ..core.config import GatewayConfig
from ..messaging import MessageBus, OutboundMessage
from ..session import SessionManager
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

    async def run(self):
        while True:
            try:
                message = await asyncio.wait_for(self.bus.consume_inbound(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            session = self.sessions.get_or_create(message.session_key)
            history = session.get_history(max_messages=50)
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
            self.sessions.save(session)

            await self.bus.publish_outbound(
                OutboundMessage(channel=message.channel, chat_id=message.chat_id, content=reply)
            )

    async def _react_loop(self, messages: list[dict]) -> str:
        final_parts: list[str] = []
        for _ in range(10):
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                tools=self.tools.get_definitions() or None,
                temperature=0.1,
                max_tokens=self.config.max_completion_tokens,
            )
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
                result = await self.tools.execute(tool_call.function.name, args)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    }
                )

        return "Max iterations reached."
