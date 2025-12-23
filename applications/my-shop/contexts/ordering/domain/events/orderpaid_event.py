"""OrderPaid 领域事件 - 智能 ID 处理"""

from dataclasses import dataclass
from datetime import datetime

from bento.core.ids import ID
from bento.domain.domain_event import DomainEvent
from bento.domain.event_registry import register_event


@register_event
@dataclass(frozen=True, kw_only=True)
class OrderPaidEvent(DomainEvent):
    """订单已支付事件

    当订单支付成功后触发，可用于：
    - 发送支付成功通知
    - 赠送会员积分
    - 记录营收指标
    - 触发物流流程

    ✅ 智能 ID 处理：
    - 创建时可直接传递 ID 对象
    - 序列化时自动转换为字符串
    - 类型安全且使用简单

    框架自动处理：
    - 事件持久化（Outbox）
    - 事件发布（消息队列）
    - 事件追踪（event_id, occurred_at）
    """

    topic: str = "order.paid"

    order_id: ID  # ✅ 支持 ID 类型
    customer_id: str  # 客户 ID 暂时保持字符串
    total: float
    paid_at: datetime
