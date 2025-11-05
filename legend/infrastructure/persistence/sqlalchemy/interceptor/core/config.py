"""SQLAlchemy拦截器配置

提供拦截器的配置管理和链构建功能。
支持配置不同类型拦截器的启用状态和自定义拦截器的添加。
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generic, List, Set, Tuple, Type, TypeVar

from .base import BatchInterceptorChain, Interceptor, InterceptorChain
from .registry import InterceptorRegistry

T = TypeVar('T')


@dataclass
class InterceptorConfig(Generic[T]):
    """拦截器配置

    控制拦截器的启用状态和行为。
    支持自定义拦截器的添加。

    Attributes:
        entity_type: 实体类型
        enable_optimistic_lock: 是否启用乐观锁
        enable_audit: 是否启用审计
        enable_soft_delete: 是否启用软删除
        custom_interceptors: 自定义拦截器列表
        context_data: 额外的配置数据
        enable_logging: 是否启用日志
        enable_cache: 是否启用缓存

    Examples:
        >>> # 创建实体的默认配置
        >>> config = InterceptorConfig.for_entity(UserPO)
        >>> 
        >>> # 创建批量操作的配置
        >>> config = InterceptorConfig.for_batch_operation(UserPO)
        >>> 
        >>> # 创建自定义配置
        >>> config = InterceptorConfig(
        ...     entity_type=UserPO,
        ...     enable_optimistic_lock=True,
        ...     enable_audit=True,
        ...     enable_soft_delete=False,
        ...     enable_logging=True,
        ...     enable_cache=True,
        ...     enable_outbox=True
        ... )
    """
    entity_type: Type[T]
    enable_optimistic_lock: bool = True
    enable_audit: bool = True
    enable_soft_delete: bool = True
    enable_logging: bool = False
    enable_cache: bool = False
    custom_interceptors: List[Interceptor[T]] = field(default_factory=list)
    context_data: Dict[str, Any] = field(default_factory=dict)

    def _is_interceptor_enabled(self, interceptor: Interceptor[T]) -> bool:
        """检查拦截器是否启用

        使用拦截器的is_enabled_in_config方法判断是否启用。

        Args:
            interceptor: 要检查的拦截器

        Returns:
            是否启用该拦截器
        """
        return interceptor.is_enabled_in_config(self)

    def create_chain(self, actor: str) -> InterceptorChain[T]:
        """创建配置的拦截器链

        根据配置创建包含所需拦截器的执行链。

        Args:
            actor: 当前操作者

        Returns:
            配置好的拦截器链
        """
        # 获取已启用的拦截器
        enabled_interceptors = self._get_enabled_interceptors(actor)

        # 创建拦截器链
        chain = InterceptorChain(enabled_interceptors)

        # 设置配置
        chain.set_config(self)

        return chain

    def create_batch_chain(self, actor: str) -> BatchInterceptorChain[T]:
        """创建批量操作的拦截器链

        根据配置创建适用于批量操作的拦截器链。

        Args:
            actor: 当前操作者

        Returns:
            批量操作的拦截器链
        """
        # 获取已启用的拦截器
        enabled_interceptors = self._get_enabled_interceptors(actor)

        # 创建批量操作拦截器链
        chain = BatchInterceptorChain(enabled_interceptors)

        # 设置配置
        chain.set_config(self)

        return chain

    def _get_enabled_interceptors(self, actor: str) -> List[Interceptor[T]]:
        """获取已启用的拦截器

        根据配置获取所有已启用的拦截器。

        Args:
            actor: 当前操作者

        Returns:
            已启用的拦截器列表
        """
        from ..impl import (
            AuditInterceptor,
            CacheInterceptor,
            LoggingInterceptor,
            OptimisticLockInterceptor,
            SoftDeleteInterceptor,
            TransactionInterceptor,
        )

        # 创建标准拦截器映射
        standard_interceptors: Dict[str, Tuple[bool, Callable[[], Interceptor[T]]]] = {
            "optimistic_lock": (
                self.enable_optimistic_lock,
                lambda: OptimisticLockInterceptor()
            ),
            "audit": (
                self.enable_audit,
                lambda: AuditInterceptor(actor)
            ),
            "soft_delete": (
                self.enable_soft_delete,
                lambda: SoftDeleteInterceptor(actor)
            ),
            "logging": (
                self.enable_logging,
                lambda: LoggingInterceptor(actor)
            ),
            "cache": (
                self.enable_cache,
                lambda: CacheInterceptor(actor)
            ),
            "transaction": (
                True,
                lambda: TransactionInterceptor(actor)
            )
        }

        # 获取已注册的拦截器
        registered_interceptors = InterceptorRegistry.get_interceptors(
            self.entity_type)

        # 过滤已注册的拦截器
        enabled_interceptors = []
        registered_types: Set[str] = set()

        # 添加已注册的拦截器
        for interceptor in registered_interceptors:
            if self._is_interceptor_enabled(interceptor):
                enabled_interceptors.append(interceptor)
                if interceptor.interceptor_type:
                    registered_types.add(interceptor.interceptor_type)

        # 添加未注册的标准拦截器
        for interceptor_type, (enabled, factory) in standard_interceptors.items():
            if enabled and interceptor_type not in registered_types:
                enabled_interceptors.append(factory())

        # 添加自定义拦截器
        for interceptor in self.custom_interceptors:
            if self._is_interceptor_enabled(interceptor):
                enabled_interceptors.append(interceptor)

        return enabled_interceptors

    @classmethod
    def for_entity(cls, entity_type: Type[T]) -> 'InterceptorConfig[T]':
        """为实体类型创建默认配置

        创建启用所有标准拦截器的配置。

        Args:
            entity_type: 实体类型

        Returns:
            默认配置
        """
        return cls(
            entity_type=entity_type,
            enable_optimistic_lock=True,
            enable_audit=True,
            enable_soft_delete=True,
            enable_logging=True,
            enable_cache=True,
        )

    @classmethod
    def for_batch_operation(
        cls,
        entity_type: Type[T],
        enable_audit: bool = True,
        enable_logging: bool = True,
        enable_cache: bool = True,
        enable_optimistic_lock: bool = False,
        enable_soft_delete: bool = False,
    ) -> 'InterceptorConfig[T]':
        """为批量操作创建配置

        创建适用于批量操作的配置，默认：
        - 禁用乐观锁（避免并发检查）
        - 启用审计（可选）
        - 禁用软删除（使用物理删除提高性能）
        - 启用出站消息（保证事件发布）
        - 禁用领域事件（批量操作通常不需要）

        Args:
            entity_type: 实体类型
            enable_audit: 是否启用审计，默认启用

        Returns:
            批量操作配置
        """
        return cls(
            entity_type=entity_type,
            enable_optimistic_lock=enable_optimistic_lock,
            enable_audit=enable_audit,
            enable_soft_delete=enable_soft_delete,
            enable_logging=enable_logging,
            enable_cache=enable_cache,
        )

    @classmethod
    def for_query(cls, entity_type: Type[T]) -> 'InterceptorConfig[T]':
        """为查询操作创建配置

        创建适用于查询操作的配置，默认：
        - 禁用所有写入相关的拦截器
        - 仅保留必要的查询拦截器

        Args:
            entity_type: 实体类型

        Returns:
            查询操作配置
        """
        return cls(
            entity_type=entity_type,
            enable_optimistic_lock=False,
            enable_audit=False,
            enable_soft_delete=False,
            enable_logging=True,
            enable_cache=True,
        )

    def add_interceptor(self, interceptor: Interceptor[T]) -> None:
        """添加自定义拦截器

        Args:
            interceptor: 要添加的拦截器
        """
        self.custom_interceptors.append(interceptor)

    def remove_interceptor(self, interceptor: Interceptor[T]) -> None:
        """移除自定义拦截器

        Args:
            interceptor: 要移除的拦截器
        """
        self.custom_interceptors = [
            i for i in self.custom_interceptors
            if i is not interceptor
        ]

    def set_context_data(self, key: str, value: Any) -> None:
        """设置上下文数据

        Args:
            key: 数据键
            value: 数据值
        """
        self.context_data[key] = value

    def get_context_data(self, key: str, default: Any = None) -> Any:
        """获取上下文数据

        Args:
            key: 数据键
            default: 默认值

        Returns:
            数据值
        """
        return self.context_data.get(key, default)
