from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Union
from uuid import UUID, uuid4

from bento.core.clock import now_utc
from bento.core.ids import ID, EntityId


@dataclass(frozen=True)
class DomainEvent:
    """Base class for all domain events.

    All domain events should inherit from this class and provide
    additional fields specific to the event type.

    ✅ 智能 ID 处理：
    - 创建事件时可以直接传递 ID 对象
    - 序列化时自动转换为字符串
    - 反序列化时可以恢复为 ID 对象

    Attributes:
        event_id: Unique identifier for this event (for idempotency)
        name: Event type name (e.g., "OrderCreated")
        occurred_at: Timestamp when the event occurred
        tenant_id: Tenant identifier for multi-tenancy support
        aggregate_id: ID of the aggregate that produced this event (智能处理 ID/str)
        schema_id: Schema identifier for event versioning
        schema_version: Schema version number

    Example:
        ```python
        @dataclass(frozen=True)
        class OrderCreatedEvent(DomainEvent):
            order_id: ID        # ✅ 可以直接使用 ID 类型
            customer_id: ID     # ✅ 框架自动处理转换
            total_amount: float

        # 创建事件 - 直接传递 ID 对象
        event = OrderCreatedEvent(
            aggregate_id=order.id,  # ✅ 直接传 ID 对象
            order_id=order.id,      # ✅ 直接传 ID 对象
            customer_id=customer.id,
            total_amount=1299.99
        )

        # 序列化 - 自动转换为字符串
        payload = event.to_payload()  # ✅ 所有 ID 自动转为字符串
        ```
    """

    # Core fields - aligned with Legend implementation
    event_id: UUID = field(default_factory=uuid4)
    name: str = ""
    occurred_at: datetime = field(default_factory=now_utc)

    # Multi-tenancy support
    tenant_id: str | None = None

    # Traceability - ✅ 智能接受 ID 或 str
    aggregate_id: ID | str | None = None

    # Versioning support
    schema_id: str | None = None
    schema_version: int = 1

    def to_payload(self) -> dict:
        """Serialize event to dictionary for storage.

        ✅ 智能序列化：自动转换所有 ID 类型为字符串

        Returns:
            Dictionary representation with all IDs converted to strings
        """
        data = asdict(self)
        return self._convert_ids_to_strings(data)

    @classmethod
    def from_payload(cls, data: dict) -> "DomainEvent":
        """Deserialize event from dictionary.

        ✅ 智能反序列化：根据类型提示恢复 ID 对象

        Args:
            data: Dictionary representation

        Returns:
            DomainEvent instance with IDs restored
        """
        converted_data = cls._convert_strings_to_ids(data, cls)
        return cls(**converted_data)

    def _convert_ids_to_strings(self, data: Any) -> Any:
        """Recursively convert ID objects to strings."""
        if isinstance(data, (ID, EntityId)):
            return str(data)
        elif isinstance(data, dict):
            return {k: self._convert_ids_to_strings(v) for k, v in data.items()}
        elif isinstance(data, (list, tuple)):
            return [self._convert_ids_to_strings(item) for item in data]
        else:
            return data

    @classmethod
    def _convert_strings_to_ids(cls, data: dict, target_class: type) -> dict:
        """Convert strings back to ID objects based on type hints."""
        from dataclasses import fields
        from typing import get_type_hints

        try:
            type_hints = get_type_hints(target_class)
            result = {}

            for field_info in fields(target_class):
                field_name = field_info.name
                field_type = type_hints.get(field_name, str)
                value = data.get(field_name)

                if value is not None:
                    result[field_name] = cls._convert_field_value(value, field_type)
                else:
                    result[field_name] = value

            return result
        except Exception:
            # 降级：如果类型推断失败，返回原始数据
            return data

    @classmethod
    def _convert_field_value(cls, value: Any, field_type: type) -> Any:
        """Convert individual field value based on type."""
        # 处理 Union 类型 (e.g., ID | str | None)
        if hasattr(field_type, "__origin__"):
            if field_type.__origin__ is Union:
                # 取第一个非 None 的类型
                args = [t for t in field_type.__args__ if t is not type(None)]
                if args and isinstance(value, str):
                    first_type = args[0]
                    if first_type == ID or (
                        hasattr(first_type, "__bases__") and EntityId in first_type.__bases__
                    ):
                        return ID(value)

        # 直接类型匹配
        if field_type == ID and isinstance(value, str):
            return ID(value)
        elif (
            hasattr(field_type, "__bases__")
            and EntityId in field_type.__bases__
            and isinstance(value, str)
        ):
            return field_type(value)

        return value
