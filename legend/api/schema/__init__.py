"""
Schema 注册监控 API 包

该包提供了 Schema 注册监控的 API 接口和可视化界面
"""

__all__ = ["create_app", "router"]

from .app import create_app
from .routes import router
