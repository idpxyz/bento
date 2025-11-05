import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Awaitable, Callable, ClassVar, Optional, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from idp.framework.infrastructure.persistence.sqlalchemy.po import BasePO
from idp.framework.infrastructure.persistence.sqlalchemy.interceptor.core.base import (
    Interceptor,
)
from idp.framework.infrastructure.persistence.sqlalchemy.interceptor.core.common import (
    InterceptorPriority,
    OperationType,
)
from idp.framework.infrastructure.persistence.sqlalchemy.interceptor.core.metadata import (
    EntityMetadataRegistry,
)
from idp.framework.infrastructure.persistence.sqlalchemy.interceptor.core.type import (
    InterceptorContext,
)

T = TypeVar('T', bound=BasePO)

logger = logging.getLogger(__name__)


@dataclass
class EntityVersionUpdated:
    """实体版本更新事件"""
    entity_id: Any
    entity_type: str
    old_version: int
    new_version: int
    operation: str
    timestamp: datetime = field(default_factory=datetime.now)

class OptimisticLockInterceptor(Interceptor[T]):
    """乐观锁拦截器
    
    通过版本号实现乐观锁，防止并发更新冲突。
    
    优先级: HIGH (100)
    配置选项:
        - enable_optimistic_lock: 是否启用乐观锁
    
    要求实体具有:
        - version: 版本号字段（可通过元数据配置）
    """
    
    interceptor_type: ClassVar[str] = "optimistic_lock"
    
    def __init__(self, config: Any = None) -> None:
        """初始化拦截器
        
        Args:
            config: 配置对象，可选
        """
        super().__init__()
        self._enabled = self.is_enabled_in_config(config) if config else True
        
    @property
    def enabled(self) -> bool:
        """是否启用拦截器"""
        return self._enabled
        
    @enabled.setter
    def enabled(self, value: bool) -> None:
        """设置拦截器启用状态"""
        self._enabled = value
    
    @property
    def priority(self) -> InterceptorPriority:
        return InterceptorPriority.HIGH
    
    def _get_version_field(self, entity_type: Type[T]) -> str:
        """获取版本字段名称"""
        metadata = EntityMetadataRegistry.get_metadata(entity_type)
        if metadata:
            return metadata.version_field
        return "version"  # 默认字段名
    
    def _should_check_version(self, context: InterceptorContext[T]) -> bool:
        """检查是否应该进行版本检查"""
        if not self.enabled or context.operation != OperationType.UPDATE:
            return False
            
        if not context.entity or not hasattr(context.entity, "id"):
            return False
            
        version_field = self._get_version_field(context.entity_type)
        if not self.has_field(context.entity, version_field):
            return False
            
        return True

    async def _notify_version_update(
        self,
        context: InterceptorContext[T],
        entity_id: Any,
        old_version: int,
        new_version: int
    ) -> None:
        """通知版本更新事件
        
        Args:
            context: 拦截器上下文
            entity_id: 实体ID
            old_version: 旧版本号
            new_version: 新版本号
        """
        event = EntityVersionUpdated(
            entity_id=entity_id,
            entity_type=context.entity_type.__name__,
            old_version=old_version,
            new_version=new_version,
            operation=context.operation.name
        )
        await self.publish_event("EntityVersionUpdated", event.__dict__)
        logger.debug(
            f"Updated version for {context.entity_type.__name__}#{entity_id}: "
            f"v{old_version} -> v{new_version}"
        )

    async def process_result(
        self,
        context: InterceptorContext[T],
        result: Any,
        next_interceptor: Callable[[InterceptorContext[T], Any], Awaitable[Any]]
    ) -> Any:
        """处理操作结果
        
        Args:
            context: 拦截器上下文
            result: 操作结果
            next_interceptor: 下一个拦截器
            
        Returns:
            处理后的结果
        """
        try:
            if not self._should_check_version(context):
                return await next_interceptor(context, result)
                
            # 获取当前事务ID (如果不存在则创建一个唯一标识)
            transaction_id = context.context_data.get("_transaction_id", id(context))
            
            # 获取已更新的实体ID集合 - 使用事务ID作为键的一部分，确保不同事务间不会冲突
            updated_entities_key = f"_updated_versions_{transaction_id}"
            updated_entities = context.context_data.setdefault(updated_entities_key, set())
            
            # logger.debug(f"Using transaction-specific version tracking with key: {updated_entities_key}")
                
            # 处理结果集
            if isinstance(result, list):
                for entity in result:
                    if not hasattr(entity, "id") or entity.id in updated_entities:
                        continue
                    await self._update_version(context, entity, updated_entities)
            elif hasattr(result, "id") and result.id not in updated_entities:
                await self._update_version(context, result, updated_entities)
            
            return await next_interceptor(context, result)
        except Exception as e:
            logger.error(f"Error in optimistic lock process_result: {str(e)}", exc_info=True)
            raise
            
    async def _update_version(
        self,
        context: InterceptorContext[T],
        entity: T,
        updated_entities: set
    ) -> None:
        """更新实体版本"""
        version_field = self._get_version_field(context.entity_type)
        current_version = getattr(entity, version_field, 0)
        new_version = current_version + 1
        
        # 更详细的日志，包含上下文信息
        logger.debug(
            f"Updating version for {context.entity_type.__name__} ID={entity.id}: "
            f"Current={current_version}, New={new_version}, "
            f"Operation={context.operation.name}, "
            f"Already tracked IDs={len(updated_entities)}"
        )
        
        # 更新版本号
        setattr(entity, version_field, new_version)
        
        # 记录已处理ID
        if entity.id in updated_entities:
            logger.warning(
                f"Entity {context.entity_type.__name__} ID={entity.id} was already version-tracked! "
                f"This indicates a potential issue with tracking."
            )
        updated_entities.add(entity.id)
        
        # 通知版本更新
        await self._notify_version_update(
            context,
            entity.id,
            current_version,
            new_version
        )

    async def _get_current_version(
        self,
        session: AsyncSession,
        entity_type: type,
        entity_id: Any
    ) -> Optional[int]:
        """获取实体当前版本号
        
        Args:
            session: 数据库会话
            entity_type: 实体类型
            entity_id: 实体ID
            
        Returns:
            当前版本号或None
        """
        stmt = select(entity_type.version).where(entity_type.id == entity_id)
        result = await session.execute(stmt)
        version = result.scalar()
        logger.debug(
            f"Current version for {entity_type.__name__}#{entity_id}: {version}"
        )
        return version

    async def after_operation(
        self,
        context: InterceptorContext[T],
        result: Any,
        next_interceptor: Callable[[InterceptorContext[T], Any], Awaitable[Any]]
    ) -> Any:
        """操作后处理
        
        如果是提交操作，清理上下文中的版本追踪信息。
        
        Args:
            context: 拦截器上下文
            result: 操作结果
            next_interceptor: 下一个拦截器
            
        Returns:
            处理后的结果
        """
        try:
            # 如果是提交操作，重置已更新实体集合
            if context.operation == OperationType.COMMIT:
                if "_updated_versions" in context.context_data:
                    entity_count = len(context.context_data["_updated_versions"])
                    if entity_count > 0:
                        logger.debug(f"Resetting version tracking for {entity_count} entities after transaction commit")
                    context.context_data["_updated_versions"] = set()
            
            return await next_interceptor(context, result)
        except Exception as e:
            logger.error(f"Error in optimistic lock after_operation: {str(e)}", exc_info=True)
            raise