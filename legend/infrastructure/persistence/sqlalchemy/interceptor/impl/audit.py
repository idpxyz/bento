from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, ClassVar, Dict, Optional, Type, TypeVar

from sqlalchemy import inspect

from idp.framework.infrastructure.persistence.sqlalchemy.po import BasePO
from idp.framework.infrastructure.persistence.sqlalchemy.interceptor.core.base import (
    Interceptor,
)
from idp.framework.infrastructure.persistence.sqlalchemy.interceptor.core.common import (
    OperationType,
)
from idp.framework.infrastructure.persistence.sqlalchemy.interceptor.core.metadata import (
    EntityMetadataRegistry,
)
from idp.framework.infrastructure.persistence.sqlalchemy.interceptor.core.type import (
    InterceptorContext,
)

T = TypeVar("T", bound=BasePO)


class AuditInterceptor(Interceptor[T]):
    """审计拦截器

    自动维护实体的审计字段（创建时间、更新时间等）。

    优先级: NORMAL (200)
    配置选项:
        - enable_audit: 是否启用审计

    要求实体具有:
        - created_at, created_by: 创建时间和创建者（可通过元数据配置）
        - updated_at, updated_by: 更新时间和更新者（可通过元数据配置）

    操作:
        - 创建时设置创建时间和创建者
        - 更新时设置更新时间和更新者
    """

    interceptor_type: ClassVar[str] = "audit"

    def __init__(self, actor: str):
        self.actor = actor
        self.next: Optional[Interceptor[T]] = None

    @classmethod
    def is_enabled_in_config(cls, config: Any) -> bool:
        """检查拦截器是否在配置中启用"""
        return getattr(config, "enable_audit", True)

    def _get_audit_fields(self, entity_type: Type[T]) -> Dict[str, str]:
        """获取审计字段映射"""
        metadata = EntityMetadataRegistry.get_metadata(entity_type)
        if metadata:
            return metadata.audit_fields

        # 默认字段映射
        return {
            "created_at": "created_at",
            "created_by": "created_by",
            "updated_at": "updated_at",
            "updated_by": "updated_by"
        }

    def _should_audit(self, context: InterceptorContext[T]) -> bool:
        """检查是否应该进行审计"""
        # 检查实体是否存在
        if not context.entity:
            return False

        # 检查是否启用审计
        return self.is_enabled_for_entity(context.entity_type)

    def _should_audit_entity(self, entity: Any, entity_type: Type[T]) -> bool:
        """检查实体是否应该审计"""
        # 检查是否启用审计
        return self.is_enabled_for_entity(entity_type)

    def _apply_create_audit(self, entity: Any, entity_type: Type[T]) -> None:
        """应用创建审计"""
        now = datetime.now(timezone.utc)

        # 获取审计字段
        fields = self._get_audit_fields(entity_type)
        created_at_field = fields.get("created_at", "created_at")
        created_by_field = fields.get("created_by", "created_by")
        updated_at_field = fields.get("updated_at", "updated_at")
        updated_by_field = fields.get("updated_by", "updated_by")

        # 设置创建时间和创建者（如果字段存在）
        if self.has_field(entity, created_at_field):
            self.set_field_value(entity, created_at_field, now)

        if self.has_field(entity, created_by_field):
            self.set_field_value(entity, created_by_field, self.actor)

        # 同时设置更新时间和更新者
        if self.has_field(entity, updated_at_field):
            self.set_field_value(entity, updated_at_field, now)

        if self.has_field(entity, updated_by_field):
            self.set_field_value(entity, updated_by_field, self.actor)

    def _apply_update_audit(self, entity: Any, entity_type: Type[T]) -> None:
        """应用更新审计"""
        now = datetime.now(timezone.utc)

        # 获取审计字段
        fields = self._get_audit_fields(entity_type)
        updated_at_field = fields.get("updated_at", "updated_at")
        updated_by_field = fields.get("updated_by", "updated_by")

        # 设置更新时间和更新者（如果字段存在）
        if self.has_field(entity, updated_at_field):
            self.set_field_value(entity, updated_at_field, now)

        if self.has_field(entity, updated_by_field):
            self.set_field_value(entity, updated_by_field, self.actor)

    async def before_operation(
        self,
        context: InterceptorContext[T],
        next_interceptor: Callable[[InterceptorContext[T]], Awaitable[Any]]
    ) -> Any:
        """操作前处理，设置审计字段"""
        if context.is_batch_operation():
            # 批量操作处理
            if not context.entities:
                return await next_interceptor(context)

            if context.operation == OperationType.BATCH_CREATE:
                for entity in context.entities:
                    if self._should_audit_entity(entity, context.entity_type):
                        self._apply_create_audit(entity, context.entity_type)

            elif context.operation == OperationType.BATCH_UPDATE:
                for entity in context.entities:
                    if self._should_audit_entity(entity, context.entity_type):
                        self._apply_update_audit(entity, context.entity_type)
        else:
            # 单个实体处理
            if not self._should_audit(context):
                return await next_interceptor(context)

            if context.operation == OperationType.CREATE:
                self._apply_create_audit(context.entity, context.entity_type)
            elif context.operation == OperationType.UPDATE:
                self._apply_update_audit(context.entity, context.entity_type)

        return await next_interceptor(context)

    async def handle_exception(
        self,
        context: InterceptorContext[T],
        error: Exception,
        next_interceptor: Callable[[
            InterceptorContext[T], Exception], Awaitable[Optional[Exception]]]
    ) -> Optional[Exception]:
        """处理异常，继续传播到下一个拦截器"""
        return await next_interceptor(context, error)

    def has_field(self, entity: Any, field_name: str) -> bool:
        """检查实体是否有指定字段，使用inspect避免触发lazy load

        Args:
            entity: 实体对象
            field_name: 字段名

        Returns:
            是否存在该字段
        """
        mapper = inspect(entity).mapper
        return field_name in mapper.attrs

    def get_field_value(self, entity: Any, field_name: str) -> Any:
        """获取字段值，如果字段不存在返回None

        Args:
            entity: 实体对象
            field_name: 字段名

        Returns:
            字段值
        """
        if not self.has_field(entity, field_name):
            return None
        return getattr(entity, field_name, None)

    async def before_create(self, context: InterceptorContext[T]) -> None:
        """创建前处理

        Args:
            context: 拦截器上下文
        """
        now = datetime.now()
        entity = context.entity

        if self.has_field(entity, "created_at"):
            entity.created_at = now
        if self.has_field(entity, "updated_at"):
            entity.updated_at = now
        if self.has_field(entity, "created_by") and context.actor:
            entity.created_by = context.actor
        if self.has_field(entity, "updated_by") and context.actor:
            entity.updated_by = context.actor
        if self.has_field(entity, "version"):
            entity.version = 1

    async def before_update(self, context: InterceptorContext[T]) -> None:
        """更新前处理

        Args:
            context: 拦截器上下文
        """
        now = datetime.now()
        entity = context.entity

        if self.has_field(entity, "updated_at"):
            entity.updated_at = now
        if self.has_field(entity, "updated_by") and context.actor:
            entity.updated_by = context.actor

    async def before_delete(self, context: InterceptorContext[T]) -> None:
        """删除前处理

        Args:
            context: 拦截器上下文
        """
        now = datetime.now()
        entity = context.entity

        if self.has_field(entity, "deleted_at"):
            entity.deleted_at = now
        if self.has_field(entity, "deleted_by") and context.actor:
            entity.deleted_by = context.actor
        if self.has_field(entity, "version"):
            current_version = self.get_field_value(entity, "version") or 0
            entity.version = current_version + 1

    async def execute(
        self,
        context: InterceptorContext[T],
        operation: Callable[[InterceptorContext[T]], T]
    ) -> T:
        """执行拦截器链

        Args:
            context: 拦截器上下文
            operation: 操作函数

        Returns:
            操作结果
        """
        if context.operation == OperationType.CREATE:
            await self.before_create(context)
        elif context.operation == OperationType.UPDATE:
            await self.before_update(context)
        elif context.operation == OperationType.DELETE:
            await self.before_delete(context)

        if self.next:
            return await self.next.execute(context, operation)
        return await operation(context)
