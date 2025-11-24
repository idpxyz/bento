"""User event handlers - 响应领域事件的应用层处理器

事件处理器用于：
- 发送通知（邮件、短信等）
- 更新读模型（CQRS）
- 触发其他业务流程
- 集成外部系统
"""

import logging

from bento.domain.event_handler import EventHandler

from contexts.identity.domain.events import (
    UserCreated,
    UserDeleted,
    UserEmailChanged,
)

logger = logging.getLogger(__name__)


class UserCreatedHandler(EventHandler[UserCreated]):
    """处理 UserCreated 事件

    责任：
    - 发送欢迎邮件
    - 记录用户注册日志
    - 更新统计数据
    """

    async def handle(self, event: UserCreated) -> None:
        """处理用户创建事件"""
        logger.info(f"User created: {event.user_id}, name={event.name}, email={event.email}")

        # TODO: 实际发送欢迎邮件
        # await email_service.send_welcome_email(event.email, event.name)

        # TODO: 更新读模型
        # await user_projection.create(event)


class UserEmailChangedHandler(EventHandler[UserEmailChanged]):
    """处理 UserEmailChanged 事件

    责任：
    - 发送邮箱验证链接到新邮箱
    - 通知旧邮箱
    - 记录安全审计日志
    """

    async def handle(self, event: UserEmailChanged) -> None:
        """处理邮箱变更事件"""
        logger.info(
            f"User email changed: {event.user_id}, from {event.old_email} to {event.new_email}"
        )

        # TODO: 发送验证邮件
        # await email_service.send_verification(event.new_email)

        # TODO: 通知旧邮箱
        # await email_service.notify_email_change(event.old_email)


class UserDeletedHandler(EventHandler[UserDeleted]):
    """处理 UserDeleted 事件

    责任：
    - 清理相关数据
    - 发送告别邮件（可选）
    - 撤销权限
    """

    async def handle(self, event: UserDeleted) -> None:
        """处理用户删除事件"""
        logger.info(f"User deleted: {event.user_id}, email={event.email}")

        # TODO: 清理相关数据
        # await cleanup_service.cleanup_user_data(event.user_id)
