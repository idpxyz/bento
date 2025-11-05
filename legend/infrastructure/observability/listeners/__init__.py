"""
可观测性监听器模块
提供针对不同组件的性能监控和链路追踪集成
"""

from typing import Optional

# 根据实际导入的监听器动态添加导出
__all__: list[str] = []

# 尝试导入 SQLAlchemy 监听器
try:
    from .sqlalchemy import SQLAlchemyListener
    __all__.append("SQLAlchemyListener")
except ImportError:
    SQLAlchemyListener: Optional[type] = None

# 尝试导入缓存监听器
try:
    from .cache import CacheListener
    __all__.append("CacheListener")
except ImportError:
    CacheListener: Optional[type] = None

# 尝试导入消息中间件监听器
try:
    from .messaging import MessagingListener
    __all__.append("MessagingListener")
except ImportError:
    MessagingListener: Optional[type] = None 