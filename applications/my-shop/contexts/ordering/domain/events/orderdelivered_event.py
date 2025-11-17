"""OrderDelivered 领域事件"""

from dataclasses import dataclass
from datetime import datetime

from bento.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class OrderDeliveredEvent(DomainEvent):
    """订单已送达事件

    当订单确认送达后触发，可用于：
    - 发送送达确认通知
    - 触发用户评价流程
    - 更新订单完成率统计
    """

    order_id: str
    delivered_at: datetime
