# MyBot

MyBot 是一个本地可调用工具的 Agent，支持通过 `cli` 或 `feishu` 运行，能够使用 `playwright-cli` 管理浏览器会话，持久化长期记忆，并从 workspace 中加载本地 skills。

## 时间线

- `2026/04/17`：提交初始版本
- `2026/04/21`：提交加入浏览器自动化能力的版本，支持 `playwright-cli`、浏览器配置、`session_map` 和 `headed`
- `2026/04/22`：完成结构整理与记忆体系改造，配置独立到 `config/`，运行数据统一到根目录 `workspace/`，并新增运行时状态层、长期记忆层和 session 摘要机制
- `2026/04/23`：完成 `llm` 多 provider 的支持，支持模型限速时的自动等待和重试
- `2026/04/24`：完成 `linux` 的支持

## TODO

- 添加更稳健的记忆管理与更新策略
- 为执行型请求补更强的工具调用兜底
- 为浏览器 session 增加更可靠的存活性检查

## 功能概览

- 本地 CLI 交互
- 可选的飞书通道
- 基于 `playwright-cli` 的浏览器自动化能力
- 本地 workspace，包含 instructions、skills、memory、sessions 和 runtime state
- 支持浏览器、文件、exec、memory 等工具的 Agent 循环
- 基于 `llm` 的多 provider 大模型配置
- 模型限速时支持自动等待并按配置重试

## 当前 Skills

本地 skills 位于：

```text
workspace/skills/
```

当前 workspace 中已有：

- `fanqie-author`
- `playwright-cli`
- `self-improving-agent`
- `weather`

## 项目结构

```text
config/
  config.json
  config.example.json

mybot/
  agent/
  core/
  messaging/
  skills/
    __init__.py
    loader.py
  storage/
    memory/
    session/
    state/
  tools/
  workspace/
    __init__.py
    bootstrap.py
  main.py

workspace/
  instructions/
    AGENTS.md
    SOUL.md
    USER.md
    TOOLS.md
  skills/
    fanqie-author/
    playwright-cli/
    self-improving-agent/
    weather/
  memory/
    memory.json
  sessions/
    *.jsonl
  state/
    runtime_state.json
```

## 配置

主配置文件：

```text
config/config.json
```

示例配置：

```text
config/config.example.json
```

项目现在统一使用顶层 `llm` 配置，不再单独使用旧的 `openai` 顶层配置。

### 示例

```json
{
  "llm": {
    "provider": "siliconflow",
    "max_completion_tokens": 20000,
    "rate_limit_retries": 2,
    "max_react_steps": 10,
    "providers": {
      "siliconflow": {
        "api_key": "YOUR_SILICONFLOW_API_KEY",
        "base_url": "https://api.siliconflow.cn/v1",
        "model": "Qwen/Qwen3-235B-A22B-Instruct-2507"
      },
      "openai": {
        "api_key": "YOUR_OPENAI_API_KEY",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4.1-mini"
      }
    }
  },
  "feishu": {
    "enabled": false,
    "app_id": "YOUR_FEISHU_APP_ID",
    "app_secret": "YOUR_FEISHU_APP_SECRET"
  },
  "workspace": {
    "path": "./workspace"
  },
  "browser": {
    "headed": true,
    "session_map": {
      "douyin.com": "douyin_main",
      "github.com": "github_main",
      "feishu.cn": "feishu_main",
      "baidu.com": "baidu_main"
    }
  },
  "debug": {
    "show_internal_process": true
  }
}
```

### `llm` 字段说明

- `llm.provider`：当前启用的 provider 名称
- `llm.providers.<name>.api_key`：对应 provider 的 API Key
- `llm.providers.<name>.base_url`：对应 provider 的 Base URL
- `llm.providers.<name>.model`：对应 provider 的模型名称
- `llm.max_completion_tokens`：单次模型响应的最大 token 数
- `llm.max_react_steps`：单次用户请求允许的最大 Agent 循环步数
- `llm.rate_limit_retries`：模型限速时允许自动重试的次数

### 其他字段说明

- `feishu.enabled`：是否启用飞书通道
- `workspace.path`：workspace 根目录
- `browser.headed`：默认是否打开可见浏览器窗口
- `browser.session_map`：将域名映射到默认浏览器 session
- `debug.show_internal_process`：是否打印内部 trace 日志

## 运行时数据

### Sessions

会话历史存放在：

```text
workspace/sessions/
```

每个会话文件是 JSONL，包含：

- 一条 `meta` 记录，用于保存会话摘要
- 用户与 assistant 的消息记录

### Memory

长期记忆存放在：

```text
workspace/memory/memory.json
```

当前 memory 结构包含：

- `user_preferences`
- `project_facts`
- `browser_preferences`
- `custom_facts`

### Runtime State

运行时浏览器状态存放在：

```text
workspace/state/runtime_state.json
```

它用于保存临时状态，例如：

- 当前活跃浏览器 session
- 最近打开的 URL
- headed 模式
- 已知浏览器 sessions

## 工具

当前默认注册的工具包括：

- `exec`
- `browser_open`
- `browser_snapshot`
- `browser_goto`
- `browser_new_tab`
- `browser_click`
- `browser_type`
- `browser_press`
- `browser_eval`
- `browser_close`
- `memory_write`
- `memory_read`
- `read_file`
- `write_file`

## 限速处理

如果模型调用触发类似 `429` 或 `TPM limit reached` 的限速错误，Agent 会：

1. 先等待 60 秒
2. 自动重试
3. 在超过 `llm.rate_limit_retries` 后停止重试并返回错误

## 启动方式

直接使用 Python 运行：

```bash
python mybot/main.py
```

Windows 本地虚拟环境下：

```bash
.venv/Scripts/python.exe mybot/main.py
```

Linux 虚拟环境下：

```bash
.venv/bin/python mybot/main.py
```

## 说明

- 浏览器工具依赖环境中可用的 `playwright-cli`
- 本地 skills 会从 `workspace/skills/*/SKILL.md` 自动发现
- API Key 建议尽量不要明文提交到仓库，使用环境变量会更安全

## Linux 迁移说明

项目现在已经对浏览器工具的进程启动方式做了 Windows / Linux 分支处理，但迁移到 Linux 仍需要准备运行环境。

至少需要：

- Python 与虚拟环境
- Node.js
- `playwright-cli`
- Playwright 需要的浏览器与系统依赖

如果 Linux 环境里没有 `playwright-cli`，浏览器工具会返回更明确的提示，而不是直接依赖 Windows 的 `cmd /c` 逻辑。
