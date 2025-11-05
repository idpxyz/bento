"""SQLAlchemy拦截器模块

提供SQLAlchemy持久化操作的拦截器功能，包括：
1. 拦截器基类和配置
2. 标准实现（乐观锁、审计、软删除等）
3. 元数据管理
4. 使用示例
"""

# 导出示例模块
from .core.base import BatchInterceptorChain, Interceptor, InterceptorChain
from .core.metadata import EntityMetadata, EntityMetadataRegistry, entity_metadata
from .core.type import InterceptorContext, OperationType
from .factory import InterceptorFactory
from .impl.audit import AuditInterceptor
from .impl.logging import LoggingInterceptor
from .impl.optimistic_lock import OptimisticLockInterceptor
from .impl.soft_delete import SoftDeleteInterceptor

__all__ = [
    # 核心类型
    "InterceptorContext",
    "OperationType",
    "Interceptor",
    "InterceptorChain",
    "BatchInterceptorChain",

    # 元数据管理
    "EntityMetadata",
    "EntityMetadataRegistry",
    "entity_metadata",

    # 工厂
    "InterceptorFactory",

    # 标准实现
    "OptimisticLockInterceptor",
    "AuditInterceptor",
    "SoftDeleteInterceptor",
    "LoggingInterceptor",

]
