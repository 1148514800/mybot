# MyBot

一个本地运行的 Agent 项目，当前支持：

- `cli` 交互
- `feishu` 渠道接入
- 基于 `playwright-cli` 的浏览器操作
- 会话历史、长期记忆、运行时状态三层分离

## 时间线

- `2026/04/17`：提交初始版本
- `2026/04/21`：提交加入浏览器自动化能力的版本，支持 `playwright-cli`、浏览器配置、`session_map` 和 `headed`
- `2026/04/22`：完成结构整理与记忆体系改造，配置独立到 `config/`，运行数据统一到根目录 `workspace/`，并新增运行时状态层、长期记忆层和 session 摘要机制

## TODO

- 添加更稳健的记忆管理与更新策略
- 为执行型请求补更强的工具调用兜底
- 为浏览器 session 增加更可靠的存活性检查

## 目录结构

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
    __init__.py
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
    playwright-cli/
    weather/
  memory/
    memory.json
  sessions/
    *.jsonl
  state/
    runtime_state.json
```

目录职责：

- `config/`：配置文件
- `workspace/instructions/`：规则与说明文件，例如 `SOUL.md`、`USER.md`
- `workspace/skills/`：本地 skill 目录
- `workspace/memory/`：长期记忆
- `workspace/sessions/`：短期会话历史
- `workspace/state/`：运行时状态
- `mybot/storage/`：对 `memory`、`session`、`state` 的代码管理层

## 配置文件

真实配置文件路径：

```text
config/config.json
```

示例配置文件路径：

```text
config/config.example.json
```

`config.json` 当前主要包含 5 个配置段：

- `openai`
- `feishu`
- `workspace`
- `browser`
- `debug`

示例：

```json
{
  "openai": {
    "api_key": "YOUR_API_KEY",
    "base_url": "https://api.siliconflow.cn/v1",
    "model": "Qwen/Qwen3-235B-A22B-Instruct-2507",
    "max_completion_tokens": 20000
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

参数说明：

- `openai.api_key`：模型接口密钥
- `openai.base_url`：兼容 OpenAI 协议的接口地址
- `openai.model`：当前使用的模型名
- `openai.max_completion_tokens`：单次补全上限
- `feishu.enabled`：是否启用飞书渠道
- `feishu.app_id` / `feishu.app_secret`：飞书配置
- `workspace.path`：工作区根目录，默认是根目录下的 `workspace/`
- `browser.headed`：默认是否以可见浏览器窗口运行
- `browser.session_map`：域名到浏览器 session 的默认映射
- `debug.show_internal_process`：是否打印内部 trace

## 会话历史

会话文件保存在：

```text
workspace/sessions/
```

当前 session 存储格式采用：

- 第一行 `meta`：保存滚动摘要
- 后续多行：保存原始消息

示意：

```json
{"type":"meta","summary":"最近在做浏览器自动化，主要操作 GitHub 和番茄小说。"}
{"role":"user","content":"打开 GitHub"}
{"role":"assistant","content":"已打开 GitHub"}
```

当前 prompt 构造时不再全量使用完整会话，而是使用：

- `session summary`
- 最近少量原始消息

这样做的目的：

- 降低 token 消耗
- 减少 assistant 旧长回复重复污染
- 保留短期上下文连续性

## 长期记忆

长期记忆文件路径：

```text
workspace/memory/memory.json
```

当前长期记忆分为几类：

- `user_preferences`
- `project_facts`
- `browser_preferences`
- `custom_facts`

其中 `custom_facts` 支持通用长期记忆项，包含：

- `key`
- `value`
- `category`
- `source`
- `updated_at`

适合写入长期记忆的内容：

- 用户偏好
- 项目长期事实
- 长期约定

不适合写入长期记忆的内容：

- 当前网页状态
- 一次性工具结果
- 临时错误

## 运行时状态

运行时状态文件路径：

```text
workspace/state/runtime_state.json
```

它用于保存“当前状态”，不是长期记忆。

当前主要记录浏览器状态，结构是按 `session` 并存：

```json
{
  "browser": {
    "active_session": "default",
    "sessions": {
      "default": {
        "last_opened_url": "https://fanqienovel.com",
        "headed": true,
        "updated_at": "2026-04-22T15:02:58.818809"
      },
      "github_main": {
        "last_opened_url": "https://github.com",
        "headed": true,
        "updated_at": "2026-04-22T15:01:53.363045"
      }
    }
  }
}
```

含义：

- `active_session`：当前活跃浏览器会话
- `sessions.<name>.last_opened_url`：该 session 当前页面
- `sessions.<name>.headed`：该 session 是否可见
- `sessions.<name>.updated_at`：最后更新时间

这层数据会在浏览器工具成功执行后自动更新。

## 浏览器能力

当前浏览器工具包括：

- `browser_open`
- `browser_goto`
- `browser_new_tab`
- `browser_snapshot`
- `browser_click`
- `browser_type`
- `browser_press`
- `browser_eval`
- `browser_close`

当前约定：

- 首次打开浏览器通常使用 `browser_open`
- 已有可复用 session 时，普通打开网站更适合使用 `browser_goto`
- 明确要求“新开一个页面/标签页”时更适合使用 `browser_new_tab`

## 启动方式

项目根目录运行：

```bash
python mybot/main.py
```

如果使用虚拟环境：

```bash
.venv/Scripts/python.exe mybot/main.py
```

## GitHub 上传注意事项

- 不要上传真实配置文件 `config/config.json`
- 仓库中使用 `config/config.example.json` 作为示例
- `workspace/sessions/`、`workspace/state/`、`workspace/memory/` 属于运行数据，通常不应直接提交
- 如果某些文件曾经已经被 git 跟踪，仅增加 `.gitignore` 还不够，需要额外从 git 索引移除
