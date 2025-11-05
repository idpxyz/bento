"""SQLAlchemy拦截器工厂

提供创建和管理拦截器的工厂方法，简化拦截器的使用。
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type, TypeVar

from idp.framework.infrastructure.cache.manager import CacheManager
from sqlalchemy.ext.asyncio import AsyncSession

from idp.framework.infrastructure.cache.core.config import CacheConfig

from .core.base import Interceptor, InterceptorChain
from .core.registry import InterceptorRegistry
from .impl import (
    AuditInterceptor,
    CacheInterceptor,
    LoggingInterceptor,
    OptimisticLockInterceptor,
    SoftDeleteInterceptor,
)
from .impl.transaction import TransactionInterceptor

T = TypeVar('T')
logger = logging.getLogger(__name__)


@dataclass
class InterceptorConfig:
    """拦截器配置类

    用于配置拦截器链的行为和依赖。所有配置项都是可选的，
    未配置的项将使用默认值。

    Examples:
        >>> config = InterceptorConfig(
        ...     actor="system",
        ...     enable_audit=True,
        ...     enable_cache=True,
        ...     cache_config={"ttl": 3600},
        ... )
        >>> chain = InterceptorFactory.create_chain(config)
    """

    # 基础配置
    actor: str = "system"

    # 功能开关
    enable_optimistic_lock: bool = True
    enable_audit: bool = True
    enable_soft_delete: bool = True
    enable_logging: bool = False
    enable_cache: bool = False

    # 外部依赖
    session: Optional[AsyncSession] = None
    cache_config: Optional[Dict[str, Any]] = None

    # 高级配置
    custom_interceptors: List[Interceptor] = field(default_factory=list)
    context_data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_kwargs(cls, **kwargs) -> 'InterceptorConfig':
        """从关键字参数创建配置实例

        支持从旧版本的参数格式创建配置实例，实现向后兼容。

        Args:
            **kwargs: 配置参数，支持新旧两种格式

        Returns:
            InterceptorConfig: 配置实例
        """
        # 移除旧版本中不再使用的参数
        kwargs.pop('entity_type', None)

        # 创建配置实例
        return cls(**{
            k: v for k, v in kwargs.items()
            if k in cls.__dataclass_fields__
        })


class InterceptorBuilder:
    """拦截器构建器，负责创建具体的拦截器实例"""

    def __init__(self, config: InterceptorConfig):
        self.config = config
        self._interceptors: List[Interceptor] = []

    def build_optimistic_lock(self) -> 'InterceptorBuilder':
        """构建乐观锁拦截器"""
        if self.config.enable_optimistic_lock:
            self._interceptors.append(OptimisticLockInterceptor())
        return self

    def build_audit(self) -> 'InterceptorBuilder':
        """构建审计拦截器"""
        if self.config.enable_audit:
            self._interceptors.append(AuditInterceptor(self.config.actor))
        return self

    def build_soft_delete(self) -> 'InterceptorBuilder':
        """构建软删除拦截器"""
        if self.config.enable_soft_delete:
            self._interceptors.append(SoftDeleteInterceptor(self.config.actor))
        return self

    def build_logging(self) -> 'InterceptorBuilder':
        """构建日志拦截器"""
        if self.config.enable_logging:
            self._interceptors.append(LoggingInterceptor())
        return self

    def build_cache(self) -> 'InterceptorBuilder':
        """构建缓存拦截器"""
        if self.config.enable_cache and self.config.cache_config:
            cache_manager = CacheManager(
                CacheConfig(**self.config.cache_config)
            )
            interceptor = CacheInterceptor(
                cache_manager=cache_manager,
                enabled=True
            )
            interceptor.cache_manager = cache_manager
            self._interceptors.append(interceptor)
        return self

    def build_transaction(self) -> 'InterceptorBuilder':
        """构建事务拦截器

        事务拦截器需要一个有效的数据库会话。如果没有提供会话，
        将抛出错误。
        """
        if not self.config.session:
            raise ValueError(
                "Cannot create TransactionInterceptor: session is required"
            )
        self._interceptors.append(TransactionInterceptor(self.config.session))
        return self

    def add_custom_interceptors(self) -> 'InterceptorBuilder':
        """添加自定义拦截器"""
        if self.config.custom_interceptors:
            self._interceptors.extend(self.config.custom_interceptors)
        return self

    def build(self) -> List[Interceptor]:
        """构建拦截器列表"""
        return self._interceptors


class InterceptorFactory:
    """拦截器工厂，负责创建和管理拦截器链"""

    _cache: Dict[str, InterceptorChain] = {}

    @classmethod
    def create_chain(
        cls,
        config: Optional[InterceptorConfig] = None,
        **kwargs
    ) -> InterceptorChain:
        """创建拦截器链

        支持两种调用方式:
        1. 使用配置对象:
           >>> chain = InterceptorFactory.create_chain(config)

        2. 使用关键字参数(向后兼容):
           >>> chain = InterceptorFactory.create_chain(
           ...     actor="system",
           ...     enable_audit=True,
           ...     session=session  # 必须提供会话
           ... )

        Args:
            config: 拦截器配置对象
            **kwargs: 配置参数(向后兼容)

        Returns:
            配置好的拦截器链

        Raises:
            ValueError: 如果没有提供数据库会话
        """
        # 如果没有提供配置对象，则从kwargs创建
        if config is None:
            config = InterceptorConfig.from_kwargs(**kwargs)

        # 验证是否提供了数据库会话
        if not config.session:
            raise ValueError(
                "Database session is required to create interceptor chain"
            )

        # 构建拦截器列表
        builder = InterceptorBuilder(config)
        interceptors = (
            builder
            .build_cache()           # 缓存优先
            .build_optimistic_lock()
            .build_audit()
            .build_soft_delete()
            .build_logging()
            .add_custom_interceptors()
            .build_transaction()     # 事务最后
            .build()
        )

        # 创建拦截器链
        chain = InterceptorChain(interceptors)

        # 记录创建的拦截器
        logger.info(
            "Created interceptor chain with %d interceptors:", len(interceptors))
        for i, interceptor in enumerate(interceptors):
            logger.info("  %d. %s", i + 1, interceptor.__class__.__name__)

        # 设置上下文数据
        if config.context_data:
            chain.set_config(config.context_data)
            logger.debug("Set context data: %s", config.context_data)

        return chain

    @classmethod
    def register_global_interceptor(
        cls,
        entity_type: Type[T],
        interceptor: Interceptor[T]
    ) -> None:
        """注册全局拦截器

        Args:
            entity_type: 实体类型
            interceptor: 拦截器
        """
        InterceptorRegistry.register(entity_type, interceptor)
        cls.clear_cache()

    @classmethod
    def clear_cache(cls) -> None:
        """清空缓存"""
        cls._cache.clear()
