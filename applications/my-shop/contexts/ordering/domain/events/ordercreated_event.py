"""OrderCreated 领域事件"""

from dataclasses import dataclass

from bento.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class OrderCreatedEvent(DomainEvent):
    """OrderCreated 事件

    开发人员只需要：
    1. 定义事件字段
    2. 在聚合根中触发事件（add_event）

    框架自动处理：
    - 事件持久化（Outbox）
    - 事件发布（消息队列）
    - 事件追踪（event_id, occurred_at）
    """

    name: str = "order_created"

    # 事件字段
    order_id: str
    customer_id: str
    total: float
    item_count: int
