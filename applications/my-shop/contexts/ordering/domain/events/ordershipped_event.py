"""OrderShipped 领域事件"""

from dataclasses import dataclass
from datetime import datetime

from bento.core.ids import ID
from bento.domain.domain_event import DomainEvent
from bento.domain.event_registry import register_event


@register_event
@dataclass(frozen=True, kw_only=True)
class OrderShippedEvent(DomainEvent):
    """订单已发货事件

    当订单发货后触发，可用于：
    - 发送发货通知给客户
    - 更新物流信息
    - 触发送达预计时间通知

    框架自动处理：
    - 事件持久化（Outbox）
    - 事件发布（消息队列）
    - 事件追踪（event_id, occurred_at）
    """

    name: str = "order_shipped"

    order_id: ID  # ✅ 支持 ID 类型
    tracking_number: str | None
    shipped_at: datetime
