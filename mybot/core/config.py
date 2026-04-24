from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from openai import OpenAI


PACKAGE_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = PACKAGE_DIR.parent
CONFIG_DIR = PROJECT_DIR / "config"
CONFIG_FILE = CONFIG_DIR / "config.json"


def _load_json_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON in {CONFIG_FILE}: {exc}") from exc


def _section(data: dict, name: str) -> dict:
    value = data.get(name, {})
    return value if isinstance(value, dict) else {}


def _config_value(data: dict, key: str, env_name: str, default=None):
    '''按优先级读取配置值：环境变量优先，其次配置字典，最后默认值。'''
    env_value = os.getenv(env_name)
    if env_value not in (None, ""):
        return env_value
    
    return data.get(key, default)


def _config_bool(data: dict, key: str, env_name: str, default: bool = False) -> bool:
    value = _config_value(data, key, env_name, default)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


_JSON_CONFIG = _load_json_config()
_LLM_CONFIG = _section(_JSON_CONFIG, "llm")
_FEISHU_CONFIG = _section(_JSON_CONFIG, "feishu")
_WORKSPACE_CONFIG = _section(_JSON_CONFIG, "workspace")
_DEBUG_CONFIG = _section(_JSON_CONFIG, "debug")
_BROWSER_CONFIG = _section(_JSON_CONFIG, "browser")


def _active_llm_provider() -> str:
    provider = str(_LLM_CONFIG.get("provider", "")).strip()
    if provider:
        return provider
    return ""


def _active_llm_config() -> dict:
    providers = _LLM_CONFIG.get("providers", {})
    if isinstance(providers, dict):
        provider_name = _active_llm_provider()
        provider_config = providers.get(provider_name, {})
        if isinstance(provider_config, dict):
            return provider_config
    return {}


_ACTIVE_LLM_PROVIDER = _active_llm_provider()
_ACTIVE_LLM_CONFIG = _active_llm_config()


def _resolve_workspace_path(raw_value: str | Path) -> Path:
    path = Path(raw_value).expanduser()
    if path.is_absolute():
        return path
    return (PROJECT_DIR / path).resolve()


@dataclass
class FeishuConfig:
    enabled: bool = field(
        default_factory=lambda: _config_bool(
            _FEISHU_CONFIG, "enabled", "MYBOT_FEISHU_ENABLED", False
        )
    )
    app_id: str = field(
        default_factory=lambda: str(
            _config_value(_FEISHU_CONFIG, "app_id", "MYBOT_FEISHU_APP_ID", "")
        ).strip()
    )
    app_secret: str = field(
        default_factory=lambda: str(
            _config_value(
                _FEISHU_CONFIG,
                "app_secret",
                "MYBOT_FEISHU_APP_SECRET",
                "",
            )
        ).strip()
    )


@dataclass
class BrowserConfig:
    headed: bool = field(
        default_factory=lambda: _config_bool(
            _BROWSER_CONFIG, "headed", "MYBOT_BROWSER_HEADED", True
        )
    )
    session_map: dict[str, str] = field(
        default_factory=lambda: {
            str(key).strip().lower(): str(value).strip()
            for key, value in _BROWSER_CONFIG.get("session_map", {}).items()
            if str(key).strip() and str(value).strip()
        }
    )


@dataclass
class GatewayConfig:
    provider: str = field(default_factory=lambda: _ACTIVE_LLM_PROVIDER)
    model: str = field(
        default_factory=lambda: _config_value(
            _ACTIVE_LLM_CONFIG, "model", "MYBOT_MODEL", "gpt-4.1-mini"
        )
    )
    rate_limit_retries: int = field(
        default_factory=lambda: int(
            _config_value(
                _LLM_CONFIG or _ACTIVE_LLM_CONFIG,
                "rate_limit_retries",
                "MYBOT_RATE_LIMIT_RETRIES",
                2,
            )
        )
    )
    max_react_steps: int = field(
        default_factory=lambda: int(
            _config_value(
                _LLM_CONFIG or _ACTIVE_LLM_CONFIG,
                "max_react_steps",
                "MYBOT_MAX_REACT_STEPS",
                10,
            )
        )
    )
    workspace: Path = field(
        default_factory=lambda: _resolve_workspace_path(
            _config_value(
                _WORKSPACE_CONFIG,
                "path",
                "MYBOT_WORKSPACE",
                PROJECT_DIR / "workspace",
            )
        )
    )
    api_key: str | None = field(
        default_factory=lambda: _config_value(_ACTIVE_LLM_CONFIG, "api_key", "OPENAI_API_KEY")
    )
    base_url: str | None = field(
        default_factory=lambda: _config_value(
            _ACTIVE_LLM_CONFIG, "base_url", "OPENAI_BASE_URL"
        )
    )
    max_completion_tokens: int = field(
        default_factory=lambda: int(
            _config_value(
                _LLM_CONFIG or _ACTIVE_LLM_CONFIG,
                "max_completion_tokens",
                "MYBOT_MAX_COMPLETION_TOKENS",
                2000,
            )
        )
    )
    show_internal_process: bool = field(
        default_factory=lambda: _config_bool(
            _DEBUG_CONFIG,
            "show_internal_process",
            "MYBOT_SHOW_INTERNAL_PROCESS",
            False,
        )
    )
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    feishu: FeishuConfig = field(default_factory=FeishuConfig)


def build_client(config: GatewayConfig) -> OpenAI:
    if not config.api_key:
        raise RuntimeError(
            f"Missing api_key for llm.provider='{config.provider}'. Set OPENAI_API_KEY or add it to {CONFIG_FILE}."
        )

    client_kwargs: dict[str, str] = {}
    client_kwargs["api_key"] = config.api_key
    if config.base_url:
        client_kwargs["base_url"] = config.base_url
    return OpenAI(**client_kwargs)
