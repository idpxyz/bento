import logging
from typing import Any, Awaitable, Callable, ClassVar, Dict, Optional, Type, TypeVar

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

T = TypeVar('T')


class SoftDeleteInterceptor(Interceptor[T]):
    """软删除拦截器

    将删除操作转换为标记删除。

    优先级: NORMAL (200)
    配置选项:
        - enable_soft_delete: 是否启用软删除

    要求实体具有:
        - is_deleted: 是否已删除（可通过元数据配置）
        - deleted_at, deleted_by: 删除时间和删除者（可通过元数据配置）

    操作:
        - 删除时标记为已删除
        - 设置删除时间和删除者
    """

    interceptor_type: ClassVar[str] = "soft_delete"

    def __init__(self, actor: str):
        self.actor = actor

    @classmethod
    def is_enabled_in_config(cls, config: Any) -> bool:
        """检查拦截器是否在配置中启用"""
        return getattr(config, "enable_soft_delete", True)

    def _get_soft_delete_fields(self, entity_type: Type[T]) -> Dict[str, str]:
        """获取软删除字段映射"""
        metadata = EntityMetadataRegistry.get_metadata(entity_type)
        if metadata:
            return metadata.soft_delete_fields

        # 默认字段映射
        return {
            "is_deleted": "is_deleted",
            "deleted_at": "deleted_at",
            "deleted_by": "deleted_by"
        }

    def _should_soft_delete(self, context: InterceptorContext[T]) -> bool:
        """检查是否应该进行软删除"""
        if context.operation != OperationType.DELETE:
            return False

        # 检查实体是否存在
        if not context.entity:
            return False

        # 获取软删除字段
        fields = self._get_soft_delete_fields(context.entity_type)
        is_deleted_field = fields.get("is_deleted", "is_deleted")

        # 检查实体是否有软删除字段
        if not self.has_field(context.entity, is_deleted_field):
            return False

        # 检查是否启用软删除
        return self.is_enabled_for_entity(context.entity_type)

    def _should_soft_delete_entity(self, entity: Any, entity_type: Type[T]) -> bool:
        """检查实体是否应该软删除"""
        # 获取软删除字段
        fields = self._get_soft_delete_fields(entity_type)
        is_deleted_field = fields.get("is_deleted", "is_deleted")

        # 检查实体是否有软删除字段
        if not self.has_field(entity, is_deleted_field):
            return False

        # 检查是否启用软删除
        return self.is_enabled_for_entity(entity_type)

    def _apply_soft_delete(self, entity: Any, entity_type: Type[T]) -> None:
        """应用软删除标记"""
        from idp.framework.shared.utils.date_time import utc_now

        logger = logging.getLogger(__name__)
        logger.debug(f"应用软删除到实体: {entity}")

        # 检查实体是否已经标记为删除
        if self.has_field(entity, "is_deleted") and getattr(entity, "is_deleted", False):
            logger.debug(f"实体已经被标记为删除，跳过: {entity}")
            return

        now = utc_now()

        # 获取软删除字段
        fields = self._get_soft_delete_fields(entity_type)
        is_deleted_field = fields.get("is_deleted", "is_deleted")
        deleted_at_field = fields.get("deleted_at", "deleted_at")
        deleted_by_field = fields.get("deleted_by", "deleted_by")

        # 设置软删除标记 - 使用显式设置而不是设置器方法
        try:
            logger.info(f"设置 {is_deleted_field}=True 到实体 {entity}")
            setattr(entity, is_deleted_field, True)

            # 设置删除时间和删除者（如果字段存在）
            if self.has_field(entity, deleted_at_field):
                logger.info(f"设置 {deleted_at_field}={now} 到实体 {entity}")
                setattr(entity, deleted_at_field, now)

            if self.has_field(entity, deleted_by_field):
                logger.info(f"设置 {deleted_by_field}={self.actor} 到实体 {entity}")
                setattr(entity, deleted_by_field, self.actor)

            # 确认设置成功
            if not getattr(entity, is_deleted_field, False):
                logger.error(
                    f"软删除标记设置失败！实体={entity}, is_deleted值={getattr(entity, is_deleted_field, None)}")
            else:
                logger.info(
                    f"软删除标记设置成功: 实体={entity}, is_deleted={getattr(entity, is_deleted_field)}, deleted_at={getattr(entity, deleted_at_field, None)}")
        except Exception as e:
            logger.error(f"应用软删除时出错: {e}, 实体={entity}", exc_info=True)
            raise

    async def before_operation(
        self,
        context: InterceptorContext[T],
        next_interceptor: Callable[[InterceptorContext[T]], Awaitable[Any]]
    ) -> Any:
        """操作前处理，处理软删除逻辑"""
        import logging
        logger = logging.getLogger(__name__)

        # 检查上下文中是否已经处理过软删除
        if context.context_data.get("delete_processed"):
            logger.debug("软删除已处理，跳过")
            return await next_interceptor(context)

        # 检查是否需要软删除
        if not self._should_soft_delete(context):
            return await next_interceptor(context)

        # 检查是否已经标记为软删除
        if context.context_data.get("soft_deleted"):
            logger.debug("检测到软删除标记")

            try:
                # 应用软删除标记
                self._apply_soft_delete(context.entity, context.entity_type)

                # 标记为已处理
                context.context_data["delete_processed"] = True

                # 修改操作类型为更新，因为这是软删除
                context.operation = OperationType.UPDATE

                # 确保实体被标记为已修改
                context.session.add(context.entity)

                # 继续处理
                result = await next_interceptor(context)

                # 确保更改被刷新到会话
                await context.session.flush()

                return result
            except Exception as e:
                logger.error(f"软删除处理失败: {e}", exc_info=True)
                raise

        # 如果没有软删除标记，继续正常处理
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
