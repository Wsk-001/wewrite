"""
Unified configuration loader for WeWrite.

现在使用 ConfigManager 确保配置只加载一次，所有模块使用同一份配置。
"""

from config_manager import get_manager, load_config, validate_config, check_startup, get_config_path

__all__ = ['load_config', 'validate_config', 'check_startup', 'get_config_path', 'get_wechat_credentials', 'get_config']


def get_config(reload=False):
    """获取配置（兼容旧 API）。
    
    Args:
        reload: 如果为 True，重新加载配置（否则返回已缓存的配置）
    
    Returns:
        Configuration dictionary
    """
    if reload:
        # 重置缓存强制重新加载
        get_manager()._config = None
        get_manager()._config_path = None
    
    return load_config()


def get_wechat_credentials() -> tuple[str, str]:
    """获取微信凭证"""
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

