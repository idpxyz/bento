"""OrderPaid 领域事件"""

from dataclasses import dataclass
from datetime import datetime

from bento.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class OrderPaidEvent(DomainEvent):
    """订单已支付事件

    当订单支付成功后触发，可用于：
    - 通知库存系统扣减库存
    - 发送支付成功通知
    - 触发物流流程
    """

    order_id: str
    customer_id: str
    total: float
    paid_at: datetime
