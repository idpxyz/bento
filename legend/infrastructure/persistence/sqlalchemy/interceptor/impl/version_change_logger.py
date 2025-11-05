import logging
from datetime import datetime
from typing import Any, Awaitable, Callable, TypeVar

from idp.framework.infrastructure.persistence.sqlalchemy.po import BasePO
from idp.framework.infrastructure.persistence.sqlalchemy.interceptor.core.base import (
    Interceptor,
)
from idp.framework.infrastructure.persistence.sqlalchemy.interceptor.core.common import (
    InterceptorPriority,
)
from idp.framework.infrastructure.persistence.sqlalchemy.interceptor.core.type import (
    InterceptorContext,
)

T = TypeVar('T', bound=BasePO)
logger = logging.getLogger(__name__)


class VersionChangeLogger(Interceptor):
    """版本号变更日志拦截器

    记录实体版本号变更的详细信息，包括：
    - 变更前后的版本号
    - 变更原因（操作类型）
    - 变更时间
    - 变更实体的标识信息
    """

    def __init__(self):
        self._logger = logging.getLogger(__name__)
        # 确保日志格式包含时间戳
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        # 添加文件处理器
        fh = logging.FileHandler('version_changes.log')
        fh.setFormatter(formatter)
        self._logger.addHandler(fh)

    @property
    def priority(self) -> InterceptorPriority:
        """拦截器优先级"""
        return InterceptorPriority.LOW

    async def before_operation(
        self,
        context: InterceptorContext,
        next_interceptor: Callable[[InterceptorContext], Awaitable[Any]]
    ) -> Any:
        """操作前记录版本号

        Args:
            context: 拦截器上下文
            next_interceptor: 下一个拦截器

        Returns:
            下一个拦截器的执行结果
        """
        if context.entity and hasattr(context.entity, 'version'):
            # 在上下文中保存当前版本号
            context.set_context_value(
                'previous_version', getattr(context.entity, 'version'))
            context.set_context_value('operation_start_time', datetime.now())

            # 保存当前状态用于比较
            if hasattr(context.entity, '__dict__'):
                context.set_context_value(
                    'previous_state', context.entity.__dict__.copy())

        # 调用下一个拦截器
        return await next_interceptor(context)

    async def after_operation(
        self,
        context: InterceptorContext,
        result: Any,
        next_interceptor: Callable[[InterceptorContext, Any], Awaitable[Any]]
    ) -> Any:
        """操作后记录版本号变更

        Args:
            context: 拦截器上下文
            result: 操作结果
            next_interceptor: 下一个拦截器

        Returns:
            操作结果
        """
        # 先调用下一个拦截器
        result = await next_interceptor(context, result)

        if context.entity and hasattr(context.entity, 'version'):
            previous_version = context.get_context_value('previous_version')
            current_version = getattr(context.entity, 'version')

            if previous_version != current_version:
                # 获取实体标识信息
                entity_id = getattr(context.entity, 'id', 'unknown')
                entity_type = context.entity.__class__.__name__

                # 获取额外的审计信息
                actor = context.get_context_value('actor', 'system')
                start_time = context.get_context_value('operation_start_time')

                # 获取变更的字段
                changed_fields = self._get_changed_fields(
                    context.entity, context)

                # 构建详细的日志消息
                log_message = (
                    f"Version Change Detected:\n"
                    f"  Entity: {entity_type} (ID: {entity_id})\n"
                    f"  Operation: {context.operation.name}\n"
                    f"  Previous Version: {previous_version}\n"
                    f"  New Version: {current_version}\n"
                    f"  Actor: {actor}\n"
                    f"  Duration: {datetime.now() - start_time if start_time else 'N/A'}\n"
                    f"  Changed Fields: {changed_fields}"
                )

                # 记录日志
                self._logger.info(log_message)

        return result

    def _get_changed_fields(self, entity: T, context: InterceptorContext) -> str:
        """获取变更的字段列表"""
        try:
            if hasattr(entity, '__dict__'):
                previous_state = context.get_context_value(
                    'previous_state', {})
                current_state = {
                    k: v for k, v in entity.__dict__.items()
                    if not k.startswith('_')
                }

                # 比较变更的字段
                changed_fields = []
                for key, current_value in current_state.items():
                    if key.startswith('_'):
                        continue
                    previous_value = previous_state.get(key)
                    if previous_value != current_value:
                        changed_fields.append(
                            f"{key}: {previous_value} -> {current_value}"
                        )

                return ", ".join(changed_fields) if changed_fields else "No field changes detected"
        except Exception as e:
            return f"Error detecting changed fields: {str(e)}"

        return "Unable to detect changed fields"
