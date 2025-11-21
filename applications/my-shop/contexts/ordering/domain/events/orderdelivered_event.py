"""OrderDelivered 领域事件"""

from dataclasses import dataclass
from datetime import datetime

from bento.core.ids import ID
from bento.domain.domain_event import DomainEvent
from bento.domain.event_registry import register_event


@register_event
@dataclass(frozen=True, kw_only=True)
class OrderDeliveredEvent(DomainEvent):
    """订单已送达事件

    当订单确认送达后触发，可用于：
    - 发送送达确认通知
    - 触发用户评价流程
    - 更新订单完成率统计

    框架自动处理：
    - 事件持久化（Outbox）
    - 事件发布（消息队列）
    - 事件追踪（event_id, occurred_at）
    """

    name: str = "order_delivered"

    order_id: ID  # ✅ 支持 ID 类型
    delivered_at: datetime
