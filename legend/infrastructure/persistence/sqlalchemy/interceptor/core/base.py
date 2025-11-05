"""SQLAlchemy拦截器基础设施

提供SQLAlchemy持久化操作的拦截器基础设施，用于处理数据库操作的横切关注点。

主要组件:
- Interceptor: 拦截器基类
- InterceptorChain: 拦截器执行链
- BatchInterceptorChain: 批量操作拦截器执行链
"""

from abc import ABC
from typing import (
    Any,
    Awaitable,
    Callable,
    ClassVar,
    Dict,
    Generic,
    List,
    Type,
    TypeVar,
)

from .common import InterceptorPriority
from .metadata import EntityMetadataRegistry
from .type import InterceptorContext

T = TypeVar('T')


class Interceptor(Generic[T], ABC):
    """拦截器基类

    定义拦截器的基本行为和生命周期方法。
    """

    # 拦截器类型标识，用于配置启用/禁用判断
    interceptor_type: ClassVar[str] = ""

    @property
    def priority(self) -> InterceptorPriority:
        """获取拦截器优先级"""
        return InterceptorPriority.NORMAL

    @classmethod
    def is_enabled_in_config(cls, config: Any) -> bool:
        """检查拦截器是否在配置中启用

        默认返回True，子类可以重写此方法以提供特定的启用逻辑。

        Args:
            config: 拦截器配置

        Returns:
            是否启用该拦截器
        """
        return True

    def is_enabled_for_entity(self, entity_type: Type[T]) -> bool:
        """检查拦截器是否对指定实体类型启用

        使用元数据注册表检查拦截器是否对实体启用。

        Args:
            entity_type: 实体类型

        Returns:
            是否启用该拦截器
        """
        if not self.interceptor_type:
            return True

        return EntityMetadataRegistry.is_feature_enabled(
            entity_type,
            self.interceptor_type
        )

    def get_entity_field(self, entity_type: Type[T], field_category: str, field_name: str) -> str:
        """获取实体字段名称

        使用元数据注册表获取实体字段的映射名称。

        Args:
            entity_type: 实体类型
            field_category: 字段类别，如"audit_fields"、"soft_delete_fields"
            field_name: 字段名称

        Returns:
            映射后的字段名称
        """
        return EntityMetadataRegistry.get_field_name(
            entity_type,
            field_category,
            field_name
        )

    def has_field(self, entity: Any, field_name: str) -> bool:
        """检查实体是否具有指定字段

        Args:
            entity: 实体对象
            field_name: 字段名称

        Returns:
            是否具有该字段
        """
        return hasattr(entity, field_name)

    def get_field_value(self, entity: Any, field_name: str, default: Any = None) -> Any:
        """获取实体字段值

        Args:
            entity: 实体对象
            field_name: 字段名称
            default: 默认值

        Returns:
            字段值
        """
        return getattr(entity, field_name, default)

    def set_field_value(self, entity: Any, field_name: str, value: Any) -> None:
        """设置实体字段值

        Args:
            entity: 实体对象
            field_name: 字段名称
            value: 字段值
        """
        setattr(entity, field_name, value)

    async def before_operation(
        self,
        context: InterceptorContext[T],
        next_interceptor: Callable[[InterceptorContext[T]], Awaitable[Any]]
    ) -> Any:
        """操作执行前的处理"""
        return await next_interceptor(context)

    async def after_operation(
        self,
        context: InterceptorContext[T],
        result: Any,
        next_interceptor: Callable[[
            InterceptorContext[T], Any], Awaitable[Any]]
    ) -> Any:
        """操作执行后的处理"""
        return await next_interceptor(context, result)

    async def on_error(
        self,
        context: InterceptorContext[T],
        error: Exception,
        next_interceptor: Callable[[
            InterceptorContext[T], Exception], Awaitable[Any]]
    ) -> Any:
        """错误处理"""
        return await next_interceptor(context, error)

    async def process_result(
        self,
        context: InterceptorContext[T],
        result: T,
        next_interceptor: Callable[[InterceptorContext[T], T], Awaitable[T]]
    ) -> T:
        """处理操作结果"""
        return await next_interceptor(context, result)

    async def handle_exception(
        self,
        context: InterceptorContext[T],
        error: Exception,
        next_interceptor: Callable[[
            InterceptorContext[T], Exception], Awaitable[Any]]
    ) -> Any:
        """处理异常

        可以转换、包装或吞噬异常。
        返回None表示异常已处理，不再传播。
        返回异常表示继续传播该异常。

        Args:
            context: 拦截器上下文
            error: 原始异常
            next_interceptor: 下一个拦截器的处理函数

        Returns:
            处理后的异常或None
        """
        # 默认实现调用on_error并继续传播异常
        return await self.on_error(context, error, next_interceptor)

    async def process_batch_results(
        self,
        context: InterceptorContext[T],
        results: List[T],
        next_interceptor: Callable[[
            InterceptorContext[T], List[T]], Awaitable[List[T]]]
    ) -> List[T]:
        """处理批量操作结果

        默认实现对每个结果调用process_result。
        子类可以重写此方法以提供批量处理逻辑。

        Args:
            context: 拦截器上下文
            results: 操作结果列表
            next_interceptor: 下一个拦截器的处理函数

        Returns:
            处理后的结果列表
        """
        processed_results = []
        for result in results:
            # 创建单个实体的上下文
            entity_context = InterceptorContext(
                session=context.session,
                entity_type=context.entity_type,
                operation=context.operation,
                entity=result,
                actor=context.actor,
                config=context.config
            )
            processed_result = await self.process_result(entity_context, result, next_interceptor)
            processed_results.append(processed_result)
        return processed_results

    async def publish_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """发布事件

        Args:
            event_type: 事件类型
            event_data: 事件数据
        """
        # 默认实现为空，子类可以重写此方法以提供事件发布功能
        pass


class InterceptorChain(Generic[T]):
    """拦截器执行链

    管理拦截器的执行顺序和生命周期。
    """

    def __init__(self, interceptors: List[Interceptor[T]] = None):
        """初始化拦截器链

        Args:
            interceptors: 拦截器列表
        """
        self.interceptors = sorted(
            interceptors or [],
            key=lambda x: x.priority,
            reverse=True
        )
        self.config = {}

    def set_config(self, config: Any) -> None:
        """设置配置

        Args:
            config: 配置对象
        """
        self.config = config

    def add_interceptor(self, interceptor: Interceptor[T]) -> None:
        """添加拦截器

        Args:
            interceptor: 要添加的拦截器
        """
        self.interceptors.append(interceptor)
        self.interceptors.sort(key=lambda x: x.priority, reverse=True)

    async def execute(
        self,
        context: InterceptorContext[T],
        operation: Callable[[], Awaitable[T]]
    ) -> T:
        """执行拦截器链

        Args:
            context: 拦截器上下文
            operation: 要执行的操作

        Returns:
            操作结果
        """
        # 设置上下文配置
        context.config = self.config

        # 创建拦截器链
        async def chain_interceptors(index: int) -> Callable:
            if index >= len(self.interceptors):
                return operation

            interceptor = self.interceptors[index]
            next_interceptor = await chain_interceptors(index + 1)

            async def execute_interceptor(ctx: InterceptorContext[T]) -> T:
                try:
                    # 执行前置处理
                    async def before_next(c: InterceptorContext[T]) -> Any:
                        return await next_interceptor(c)
                    await interceptor.before_operation(ctx, before_next)

                    # 执行操作
                    result = await next_interceptor(ctx)

                    # 执行后置处理
                    async def after_next(c: InterceptorContext[T], r: Any) -> Any:
                        return r
                    result = await interceptor.after_operation(ctx, result, after_next)

                    # 处理结果
                    async def process_next(c: InterceptorContext[T], r: T) -> T:
                        return r
                    result = await interceptor.process_result(ctx, result, process_next)

                    return result
                except Exception as e:
                    # 处理异常
                    async def handle_next(c: InterceptorContext[T], err: Exception) -> Any:
                        return err
                    handled = await interceptor.handle_exception(ctx, e, handle_next)
                    if handled is not None:
                        raise handled
                    return None

            return execute_interceptor

        # 执行拦截器链
        chain = await chain_interceptors(0)
        return await chain(context)


class BatchInterceptorChain(InterceptorChain[T]):
    """批量操作拦截器链

    支持批量操作的拦截器执行链。
    """

    async def execute_batch(
        self,
        context: InterceptorContext[T],
        entities: List[T],
        operation: Callable[[
            List[T], InterceptorContext[T]], Awaitable[List[T]]]
    ) -> List[T]:
        """批量执行操作

        Args:
            context: 拦截器上下文
            entities: 实体列表
            operation: 批量操作函数

        Returns:
            操作结果列表
        """
        # 设置批量操作的实体列表
        context.entities = entities

        # 设置上下文配置
        if self.config and context.config is None:
            context.config = self.config

        try:
            # 前置处理（只执行一次）
            for interceptor in self.interceptors:
                await interceptor.before_operation(context)

            # 执行批量操作，传递上下文
            results = await operation(entities, context)

            # 处理批量结果
            for interceptor in self.interceptors:
                results = await interceptor.process_batch_results(context, results)

            # 后置处理（只执行一次）
            for interceptor in reversed(self.interceptors):
                await interceptor.after_operation(context)

            return results

        except Exception as e:
            # 增强的错误处理
            current_error = e

            # 按优先级顺序处理异常
            for interceptor in self.interceptors:
                handled_error = await interceptor.handle_exception(context, current_error)

                # 如果拦截器处理了异常（返回None），则停止传播
                if handled_error is None:
                    return []

                # 更新当前异常
                current_error = handled_error

            # 如果没有拦截器完全处理异常，则重新抛出
            raise current_error
