from __future__ import annotations

import asyncio

from ..agent import AgentLoop, ContextBuilder
from ..messaging import CLIChannel, FeishuChannel, BaseChannel, MessageBus, route_outbound
from ..session import SessionManager
from ..tools import build_default_tool_registry
from ..workspace import init_workspace
from .config import GatewayConfig, build_client


async def run_gateway(config: GatewayConfig | None = None) -> None:
    config = config or GatewayConfig()  # 获取配置文件
    init_workspace(config.workspace)    # 初始化工作目录

    bus = MessageBus()  # 消息总线
    tools = build_default_tool_registry(config.workspace)   # 构建工具注册表，包含一些默认工具，比如执行命令、读写文件等
    context = ContextBuilder(config.workspace)  # 构建上下文生成器，负责根据工作目录下的文件和工具注册表生成系统提示和对话历史
    sessions = SessionManager(config.workspace) # 会话管理器，负责存储和加载用户的对话历史，按 channel:chat_id 进行区分
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

    await asyncio.gather(
        agent.run(),
        route_outbound(bus, channels),
        *[channel.start() for channel in channels.values()],
    )
