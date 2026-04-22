from __future__ import annotations

import asyncio

from ..agent import AgentLoop, ContextBuilder
from ..messaging import CLIChannel, FeishuChannel, BaseChannel, MessageBus, route_outbound
from ..storage.memory import MemoryManager
from ..storage.session import SessionManager
from ..storage.state import StateManager
from ..tools import build_default_tool_registry
from ..workspace import init_instructions, init_workspace
from .config import GatewayConfig, build_client


async def run_gateway(config: GatewayConfig | None = None) -> None:
    config = config or GatewayConfig()  # 初始化配置
    init_instructions(config.workspace / "instructions")    # 初始化智能体角色
    init_workspace(config.workspace)    # 初始化工作空间

    bus = MessageBus()  # 消息总线
    memory = MemoryManager(config.workspace)    # 初始化长期记忆
    state = StateManager(config.workspace)  # 初始化运行状态
    tools = build_default_tool_registry(config.workspace, config.browser, state, memory)    # 初始化工具
    context = ContextBuilder(config.workspace, state_manager=state, memory_manager=memory)  # 构建上下文
    sessions = SessionManager(config.workspace) # 保存短期会话历史
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
