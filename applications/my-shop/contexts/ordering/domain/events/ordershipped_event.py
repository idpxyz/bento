"""OrderShipped 领域事件"""

from dataclasses import dataclass
from datetime import datetime

from bento.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class OrderShippedEvent(DomainEvent):
    """订单已发货事件

    当订单发货后触发，可用于：
    - 发送发货通知给客户
    - 更新物流信息
    - 触发送达预计时间通知
    """

    order_id: str
    tracking_number: str | None
    shipped_at: datetime
