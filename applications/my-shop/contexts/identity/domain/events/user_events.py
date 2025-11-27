"""User domain events.

领域事件表示领域中发生的重要业务事实。
事件是不可变的，代表过去发生的事情。
"""

from datetime import datetime
from uuid import UUID

from bento.core.ids import ID
from bento.domain.domain_event import DomainEvent
from bento.domain.event_registry import register_event


@register_event
class UserCreated(DomainEvent):
    """User created event.

    当新用户被创建时发布此事件。

    用途：
    - 发送欢迎邮件
    - 记录用户注册日志
    - 更新统计数据
    - 同步到其他系统

    Attributes:
        user_id: 用户 ID
        name: 用户名称
        email: 用户邮箱
    """

    user_id: ID
    name: str
    email: str

    def __init__(
        self,
        user_id: ID | str,
        name: str,
        email: str,
        *,
        event_id: UUID | None = None,
        name_override: str = "UserCreated",
        occurred_at: datetime | None = None,
        tenant_id: str | None = None,
        aggregate_id: str | None = None,
        schema_id: str | None = None,
        schema_version: int = 1,
        **_: object,
    ) -> None:
        """Initialize UserCreated event."""
        uid = user_id if isinstance(user_id, ID) else ID(user_id)

        _super_kwargs: dict[str, object] = {
            "name": name_override,
            "aggregate_id": aggregate_id or str(uid),
            "schema_version": schema_version,
        }
        if event_id:
            _super_kwargs["event_id"] = event_id
        if occurred_at:
            _super_kwargs["occurred_at"] = occurred_at
        if tenant_id:
            _super_kwargs["tenant_id"] = tenant_id
        if schema_id:
            _super_kwargs["schema_id"] = schema_id

        super().__init__(**_super_kwargs)

        self.user_id = uid
        self.name = name
        self.email = email


@register_event
class UserUpdated(DomainEvent):
    """User updated event.

    当用户信息被更新时发布此事件。

    用途：
    - 同步用户信息到其他系统
    - 审计日志记录
    - 缓存失效

    Attributes:
        user_id: 用户 ID
        updated_fields: 更新的字段及其新值
    """

    user_id: ID
    updated_fields: dict[str, str]

    def __init__(
        self,
        user_id: ID | str,
        updated_fields: dict[str, str],
        *,
        event_id: UUID | None = None,
        topic: str = "UserUpdated",
        occurred_at: datetime | None = None,
        tenant_id: str | None = None,
        aggregate_id: str | None = None,
        schema_id: str | None = None,
        schema_version: int = 1,
        **_: object,
    ) -> None:
        """Initialize UserUpdated event."""
        uid = user_id if isinstance(user_id, ID) else ID(user_id)

        _super_kwargs: dict[str, object] = {
            "topic": topic,
            "aggregate_id": aggregate_id or str(uid),
            "schema_version": schema_version,
        }
        if event_id:
            _super_kwargs["event_id"] = event_id
        if occurred_at:
            _super_kwargs["occurred_at"] = occurred_at
        if tenant_id:
            _super_kwargs["tenant_id"] = tenant_id
        if schema_id:
            _super_kwargs["schema_id"] = schema_id

        super().__init__(**_super_kwargs)

        self.user_id = uid
        self.updated_fields = updated_fields


@register_event
class UserDeleted(DomainEvent):
    """User deleted event.

    当用户被删除（软删除）时发布此事件。

    用途：
    - 清理相关数据
    - 发送告别邮件（可选）
    - 审计日志
    - 撤销权限

    Attributes:
        user_id: 用户 ID
        email: 用户邮箱（用于通知）
    """

    user_id: ID
    email: str

    def __init__(
        self,
        user_id: ID | str,
        email: str,
        *,
        event_id: UUID | None = None,
        topic: str = "UserDeleted",
        occurred_at: datetime | None = None,
        tenant_id: str | None = None,
        aggregate_id: str | None = None,
        schema_id: str | None = None,
        schema_version: int = 1,
        **_: object,
    ) -> None:
        """Initialize UserDeleted event."""
        uid = user_id if isinstance(user_id, ID) else ID(user_id)

        _super_kwargs: dict[str, object] = {
            "topic": topic,
            "aggregate_id": aggregate_id or str(uid),
            "schema_version": schema_version,
        }
        if event_id:
            _super_kwargs["event_id"] = event_id
        if occurred_at:
            _super_kwargs["occurred_at"] = occurred_at
        if tenant_id:
            _super_kwargs["tenant_id"] = tenant_id
        if schema_id:
            _super_kwargs["schema_id"] = schema_id

        super().__init__(**_super_kwargs)

        self.user_id = uid
        self.email = email


@register_event
class UserEmailChanged(DomainEvent):
    """User email changed event.

    当用户邮箱被更改时发布此事件。
    这是一个独立的事件，因为邮箱变更通常需要特殊处理（验证等）。

    用途：
    - 发送邮箱验证链接
    - 通知旧邮箱
    - 安全审计

    Attributes:
        user_id: 用户 ID
        old_email: 旧邮箱
        new_email: 新邮箱
    """

    user_id: ID
    old_email: str
    new_email: str

    def __init__(
        self,
        user_id: ID | str,
        old_email: str,
        new_email: str,
        *,
        event_id: UUID | None = None,
        topic: str = "UserEmailChanged",
        occurred_at: datetime | None = None,
        tenant_id: str | None = None,
        aggregate_id: str | None = None,
        schema_id: str | None = None,
        schema_version: int = 1,
        **_: object,
    ) -> None:
        """Initialize UserEmailChanged event."""
        uid = user_id if isinstance(user_id, ID) else ID(user_id)

        _super_kwargs: dict[str, object] = {
            "topic": topic,
            "aggregate_id": aggregate_id or str(uid),
            "schema_version": schema_version,
        }
        if event_id:
            _super_kwargs["event_id"] = event_id
        if occurred_at:
            _super_kwargs["occurred_at"] = occurred_at
        if tenant_id:
            _super_kwargs["tenant_id"] = tenant_id
        if schema_id:
            _super_kwargs["schema_id"] = schema_id

        super().__init__(**_super_kwargs)

        self.user_id = uid
        self.old_email = old_email
        self.new_email = new_email
