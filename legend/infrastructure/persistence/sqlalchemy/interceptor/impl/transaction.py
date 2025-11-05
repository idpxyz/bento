"""事务拦截器实现

本模块提供事务拦截器的实现，用于协助工作单元管理事务。
主要负责：
1. 事务传播行为
2. 嵌套事务处理
3. 与工作单元事务的协调
"""

import logging
from typing import Any, Awaitable, Callable, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from idp.framework.infrastructure.persistence.sqlalchemy.interceptor.core.base import Interceptor
from idp.framework.infrastructure.persistence.sqlalchemy.interceptor.core.common import (
    InterceptorPriority,
    OperationType,
)
from idp.framework.infrastructure.persistence.sqlalchemy.interceptor.core.type import InterceptorContext

logger = logging.getLogger(__name__)

class TransactionInterceptor(Interceptor):
    """事务拦截器
    
    作为事务协作者，负责：
    1. 与工作单元的事务管理协同工作
    2. 处理事务传播行为
    3. 管理嵌套事务
    
    该拦截器通常配合工作单元使用，不应独立管理事务。
    """
    
    def __init__(self, session: AsyncSession):
        """初始化事务拦截器
        
        Args:
            session: SQLAlchemy异步会话
        """
        self.session = session
        
    @property
    def priority(self) -> int:
        """获取拦截器优先级
        
        事务拦截器应该具有最高优先级，以确保在其他拦截器之前执行。
        
        Returns:
            拦截器优先级
        """
        return InterceptorPriority.HIGHEST
    
    async def before_operation(
        self, 
        context: InterceptorContext, 
        next_interceptor: Callable[[InterceptorContext], Awaitable[Any]]
    ) -> Any:
        """在操作之前执行
        
        检查当前事务状态，确保操作在正确的事务上下文中执行。
        
        Args:
            context: 拦截器上下文
            next_interceptor: 下一个拦截器
            
        Returns:
            操作结果
        """
        if not self._needs_transaction(context.operation):
            return await next_interceptor(context)
            
        # 检查是否已存在活动事务
        has_active_transaction = self.session.in_transaction()
        if not has_active_transaction:
            logger.warning(
                f"Operation {context.operation} executed without an active transaction. "
                "Consider using a UnitOfWork to manage transactions."
            )
            
        # 继续执行，让工作单元管理事务
        return await next_interceptor(context)
    
    async def handle_exception(
        self, 
        context: InterceptorContext, 
        exception: Exception, 
        next_interceptor: Callable[[InterceptorContext, Exception], Awaitable[Any]]
    ) -> Any:
        """处理异常
        
        记录异常信息，但让工作单元处理事务回滚。
        
        Args:
            context: 拦截器上下文
            exception: 异常
            next_interceptor: 下一个拦截器
            
        Returns:
            处理结果
        """
        if self._needs_transaction(context.operation):
            logger.error(
                f"Error in transaction for operation {context.operation}: {str(exception)}"
            )
            
        # 继续传播异常，让工作单元处理回滚
        return await next_interceptor(context, exception)
    
    def _needs_transaction(self, operation: OperationType) -> bool:
        """检查操作是否需要事务
        
        写操作（创建、更新、删除）需要事务，读操作不需要。
        
        Args:
            operation: 操作类型
            
        Returns:
            如果需要事务则为True，否则为False
        """
        return operation in [
            OperationType.CREATE,
            OperationType.UPDATE,
            OperationType.DELETE,
            OperationType.BATCH_CREATE,
            OperationType.BATCH_UPDATE,
            OperationType.BATCH_DELETE
        ] 