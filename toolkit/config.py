"""
Unified configuration loader for WeWrite.

Single source of truth for config loading. Environment variables
override config.yaml values for sensitive fields.

Environment variable mapping:
    WECHAT_APPID          \u2192 wechat.appid
    WECHAT_SECRET         \u2192 wechat.secret
    WECHAT_AUTHOR         \u2192 wechat.author
    WEWRITE_IMAGE_PROVIDER \u2192 image.provider
    WEWRITE_IMAGE_API_KEY  \u2192 image.api_key
    WEWRITE_IMAGE_MODEL    \u2192 image.model
    WEWRITE_THEME          \u2192 theme
"""

import os
from pathlib import Path

import yaml

SKILL_DIR = Path(__file__).parent.parent
TOOLKIT_DIR = Path(__file__).parent

CONFIG_SEARCH_ORDER = [
    SKILL_DIR / "config" / "config.yaml",
    SKILL_DIR / "config.yaml",
    TOOLKIT_DIR / "config.yaml",
    Path.home() / ".config" / "wewrite" / "config.yaml",
]

_ENV_OVERRIDES = {
    ("wechat", "appid"): "WECHAT_APPID",
    ("wechat", "secret"): "WECHAT_SECRET",
    ("wechat", "author"): "WECHAT_AUTHOR",
    ("image", "provider"): "WEWRITE_IMAGE_PROVIDER",
    ("image", "api_key"): "WEWRITE_IMAGE_API_KEY",
    ("image", "model"): "WEWRITE_IMAGE_MODEL",
    ("theme",): "WEWRITE_THEME",
}

_cached_config: dict | None = None
_cached_path: Path | None = None


def load_config(force_reload: bool = False) -> dict:
    """Load config with caching. Environment variables override file values."""
    global _cached_config, _cached_path

    if _cached_config is not None and not force_reload:
        return _cached_config

    config = {}
    for p in CONFIG_SEARCH_ORDER:
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
            _cached_path = p
            break

    for keys, env_var in _ENV_OVERRIDES.items():
        val = os.environ.get(env_var)
        if val is None:
            continue
        if len(keys) == 1:
            config[keys[0]] = val
        elif len(keys) == 2:
            config.setdefault(keys[0], {})[keys[1]] = val

    _cached_config = config
    return config


def get_config_path() -> Path | None:
    if _cached_path is None:
        load_config()
    return _cached_path


def get_wechat_credentials() -> tuple[str, str]:
    cfg = load_config()
    wechat = cfg.get("wechat", {})
    appid = wechat.get("appid", "")
    secret = wechat.get("secret", "")
    if not appid or not secret:
        raise ValueError(
            "WeChat credentials not found. Set WECHAT_APPID + WECHAT_SECRET "
            "environment variables, or configure wechat.appid/secret in config.yaml"
        )
    return appid, secret
