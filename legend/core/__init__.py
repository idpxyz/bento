"""
IDP框架核心模块，包含配置、中间件、依赖项等基础功能
""" 

from idp.framework.core.config import app_settings, exception_settings

__all__ = [
    "app_settings",
    "exception_settings",
]
