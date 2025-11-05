import logging
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, ClassVar, Optional, TypeVar

from idp.framework.infrastructure.persistence.sqlalchemy.interceptor.core.base import Interceptor
from idp.framework.infrastructure.persistence.sqlalchemy.interceptor.core.common import InterceptorPriority
from idp.framework.infrastructure.persistence.sqlalchemy.interceptor.core.type import InterceptorContext

T = TypeVar('T')

class LoggingInterceptor(Interceptor[T]):
    """日志拦截器
    
    记录数据库操作的日志。
    
    优先级: LOWEST (400)
    配置选项:
        - 无特定配置
    
    操作:
        - 记录操作开始、结束和错误日志
    """
    
    interceptor_type: ClassVar[str] = "logging"
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
    
    @property
    def priority(self) -> InterceptorPriority:
        return InterceptorPriority.LOWEST
    
    async def before_operation(
        self, 
        context: InterceptorContext[T],
        next_interceptor: Callable[[InterceptorContext[T]], Awaitable[Any]]
    ) -> Any:
        """操作前记录日志"""
        # 只在DEBUG级别记录详细的开始日志，减少日志量
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(
                f"Starting {context.operation} operation on {context.entity_type.__name__}"
            )
        
        # 存储开始时间用于计算执行时间
        context.context_data["start_time"] = datetime.now(timezone.utc)
        
        # 执行下一个拦截器
        return await next_interceptor(context)
    
    async def after_operation(
        self,
        context: InterceptorContext[T],
        result: Any,
        next_interceptor: Callable[[InterceptorContext[T], Any], Awaitable[Any]]
    ) -> Any:
        """记录操作结束日志"""
        entity_id = self._get_entity_id(context)
        start_time = context.context_data.get("start_time")
        
        if start_time:
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            # 使用INFO级别记录完成信息，避免与DEBUG级别的其他日志重复
            self.logger.info(
                f"{context.operation.name} completed on "
                f"{context.entity_type.__name__} "
                f"(ID: {entity_id}) in {duration:.3f}s"
            )
        else:
            self.logger.info(
                f"{context.operation.name} completed on "
                f"{context.entity_type.__name__} "
                f"(ID: {entity_id})"
            )
            
        # 执行下一个拦截器
        return await next_interceptor(context, result)
    
    async def handle_exception(
        self, 
        context: InterceptorContext[T], 
        error: Exception,
        next_interceptor: Callable[[InterceptorContext[T], Exception], Awaitable[Optional[Exception]]]
    ) -> Optional[Exception]:
        """记录操作错误日志"""
        entity_id = self._get_entity_id(context)
        
        self.logger.error(
            f"Operation {context.operation.name} failed on "
            f"{context.entity_type.__name__} "
            f"(ID: {entity_id}): {error}",
            exc_info=error
        )
        
        # 执行下一个拦截器
        return await next_interceptor(context, error)
    
    def _get_entity_id(self, context: InterceptorContext[T]) -> str:
        """获取实体ID"""
        if context.entity and hasattr(context.entity, 'id'):
            return str(context.entity.id)
        elif context.entities and hasattr(context.entities[0], 'id'):
            return f"[{', '.join(str(e.id) for e in context.entities if hasattr(e, 'id'))}]"
        else:
            return "unknown" 