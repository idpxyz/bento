"""ProductCreated 领域事件"""

from dataclasses import dataclass, field

from bento.domain.domain_event import DomainEvent
from bento.domain.event_registry import register_event


@register_event
@dataclass(frozen=True)
class ProductCreated(DomainEvent):
    """ProductCreated 事件

    开发人员只需要：
    1. 定义事件字段
    2. 在聚合根中触发事件（add_event）

    框架自动处理：
    - 事件持久化（Outbox）
    - 事件发布（消息队列）
    - 事件追踪（event_id, occurred_at）
    """

    # 事件字段
    product_id: str = field(default="")
    name: str = field(default="")
    price: float = field(default=0.0)

    # 可选字段
    sku: str | None = field(default=None)
    brand: str | None = field(default=None)

    # 元数据（必须放在最后）
    topic: str = field(default="catalog.product.created")
    # new_value: str
