"""OrderCancelled 领域事件"""

from dataclasses import dataclass

from bento.core.ids import ID
from bento.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class OrderCancelledEvent(DomainEvent):
    """订单已取消事件

    当订单被取消后触发，可用于：
    - 释放库存
    - 处理退款（如果已支付）
    - 发送取消通知
    - 分析取消原因
    """

    order_id: ID  # ✅ 支持 ID 类型
    reason: str
    previous_status: str  # 取消前的状态
