"""
统一配置管理器

所有模块都通过这个入口加载配置，确保一致性和透明性。
- 只加载一次配置（缓存机制）
- 启动时验证配置完整性
- 打印配置信息给用户看
- 出错时立刻报错，不会无声失败
"""

import os
import sys
from pathlib import Path
from typing import Optional, Tuple

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


class ConfigManager:
    """单例配置管理器"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._config = None
        self._config_path = None
        self._validated = False
        self._initialized = True
    
    def load(self, force_reload: bool = False) -> dict:
        """
        加载配置，只加载一次（除非 force_reload=True）
        
        返回：配置字典
        """
        if self._config is not None and not force_reload:
            return self._config
        
        # 搜索配置文件
        config = {}
        for p in CONFIG_SEARCH_ORDER:
            if p.exists():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        config = yaml.safe_load(f) or {}
                    self._config_path = p
                    break
                except Exception as e:
                    print(f"[ERROR] Failed to load config from {p}: {e}", file=sys.stderr)
                    sys.exit(1)
        
        # 应用环境变量覆盖
        for keys, env_var in _ENV_OVERRIDES.items():
            val = os.environ.get(env_var)
            if val is None:
                continue
            if len(keys) == 1:
                config[keys[0]] = val
            elif len(keys) == 2:
                config.setdefault(keys[0], {})[keys[1]] = val
        
        self._config = config
        return config
    
    def get_config_path(self) -> Optional[Path]:
        """获取配置文件路径"""
        if self._config is None:
            self.load()
        return self._config_path
    
    def validate(self) -> Tuple[bool, list]:
        """
        验证配置完整性
        
        返回：(是否有效, 错误列表)
        """
        if self._validated:
            return True, []
        
        errors = []
        config = self.load()
        
        # 检查 WeChat 配置
        wechat = config.get("wechat", {})
        if not wechat.get("appid"):
            errors.append("Missing: wechat.appid")
        if not wechat.get("secret"):
            errors.append("Missing: wechat.secret")
        
        # 检查图片 API 配置
        image = config.get("image", {})
        providers = image.get("providers", [])
        
        if not providers:
            # 如果没有 providers 列表，检查旧格式
            if not image.get("provider"):
                errors.append("Missing: image.providers (list) or image.provider")
            if not image.get("api_key"):
                errors.append("Missing: image.api_key")
        else:
            # 检查 providers 列表中的每一项
            for i, provider in enumerate(providers):
                if not provider.get("provider"):
                    errors.append(f"Missing: image.providers[{i}].provider")
                if not provider.get("api_key"):
                    errors.append(f"Missing: image.providers[{i}].api_key")
        
        # 检查主题（可选，有默认值）
        if not config.get("theme"):
            print("[WARNING] theme not set, will use default: moyu-green", file=sys.stderr)
        
        # 检查作者（可选）
        author = config.get("author") or wechat.get("author")
        if not author:
            print("[WARNING] author not set in config", file=sys.stderr)
        
        if errors:
            self._validated = False
            return False, errors
        
        self._validated = True
        return True, []
    
    def log_startup_info(self):
        """
        启动时打印配置信息
        向用户透明地展示当前使用的配置
        """
        config = self.load()
        config_path = self.get_config_path()
        
        print("[INFO] Configuration loaded", file=sys.stderr)
        if config_path:
            print(f"[INFO] Config file: {config_path}", file=sys.stderr)
        else:
            print("[INFO] Config file: using defaults (no file found)", file=sys.stderr)
        
        wechat = config.get("wechat", {})
        appid = wechat.get("appid", "NOT SET")
        if appid != "NOT SET" and len(appid) > 12:
            appid_display = appid[:8] + "..." + appid[-4:]
        else:
            appid_display = appid
        print(f"[INFO]   WeChat AppID: {appid_display}", file=sys.stderr)
        
        # 显示图片 API 配置
        image = config.get("image", {})
        providers = image.get("providers", [])
        
        if providers:
            for i, p in enumerate(providers):
                provider_name = p.get("provider", "unknown")
                model = p.get("model", "default")
                print(f"[INFO]   Image Provider[{i}]: {provider_name} ({model})", file=sys.stderr)
        else:
            provider = image.get("provider", "NOT SET")
            model = image.get("model", "default")
            if provider != "NOT SET":
                print(f"[INFO]   Image Provider: {provider} ({model})", file=sys.stderr)
        
        # 显示主题
        theme = config.get("theme", "moyu-green (default)")
        print(f"[INFO]   Theme: {theme}", file=sys.stderr)
        
        # 显示作者
        author = config.get("author") or wechat.get("author", "NOT SET")
        print(f"[INFO]   Author: {author}", file=sys.stderr)
        
        print("[INFO] Configuration ready ✓", file=sys.stderr)
    
    def check_startup(self) -> bool:
        """
        启动检查：加载配置、验证、打印信息
        
        如果有问题，打印错误并返回 False
        """
        # 第1步：加载配置
        try:
            self.load()
        except Exception as e:
            print(f"[ERROR] Failed to load config: {e}", file=sys.stderr)
            return False
        
        # 第2步：验证配置
        valid, errors = self.validate()
        if not valid:
            print("[ERROR] Config validation failed:", file=sys.stderr)
            for err in errors:
                print(f"[ERROR]   - {err}", file=sys.stderr)
            return False
        
        # 第3步：打印配置信息
        self.log_startup_info()
        
        return True


# 全局单例实例
_config_manager = None

def get_manager() -> ConfigManager:
    """获取配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def load_config(force_reload: bool = False) -> dict:
    """加载配置（兼容旧 API）"""
    return get_manager().load(force_reload)


def validate_config() -> bool:
    """验证配置（兼容旧 API）"""
    valid, _ = get_manager().validate()
    return valid


def check_startup() -> bool:
    """启动检查"""
    return get_manager().check_startup()


def get_config_path() -> Optional[Path]:
    """获取配置文件路径（兼容旧 API）"""
    return get_manager().get_config_path()
