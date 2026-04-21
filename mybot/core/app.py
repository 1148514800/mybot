from __future__ import annotations

import asyncio

from ..agent import AgentLoop, ContextBuilder
from ..messaging import CLIChannel, FeishuChannel, BaseChannel, MessageBus, route_outbound
from ..session import SessionManager
from ..tools import build_default_tool_registry
from ..workspace import init_workspace
from .config import GatewayConfig, build_client


async def run_gateway(config: GatewayConfig | None = None) -> None:
    config = config or GatewayConfig()
    init_workspace(config.workspace)

    bus = MessageBus()
    tools = build_default_tool_registry(config.workspace, config.browser)
    context = ContextBuilder(config.workspace)
    sessions = SessionManager(config.workspace)
    agent = AgentLoop(
        client=build_client(config),
        config=config,
        bus=bus,
        tools=tools,
        context=context,
        sessions=sessions,
    )

    channels: dict[str, BaseChannel] = {"cli": CLIChannel(bus)}

    if config.feishu.enabled and config.feishu.app_id and config.feishu.app_secret:
        channels["feishu"] = FeishuChannel(
            bus,
            app_id=config.feishu.app_id,
            app_secret=config.feishu.app_secret,
        )
    else:
        print("Feishu channel disabled. Set feishu config to enable it.")

    print(f"Gateway started. Channels: {list(channels.keys())}\n")
    print(f"Internal process trace: {config.show_internal_process}\n")

    await asyncio.gather(
        agent.run(),
        route_outbound(bus, channels),
        *[channel.start() for channel in channels.values()],
    )
