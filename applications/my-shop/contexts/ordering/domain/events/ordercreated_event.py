"""OrderCreated 领域事件"""

from dataclasses import dataclass

from bento.domain.domain_event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class OrderCreatedEvent(DomainEvent):
    """OrderCreated 事件 - 包含完整订单信息

    包含订单的完整信息，使下游服务能够：
    - 库存服务：立即扣减库存
    - 通知服务：发送详细订单确认邮件
    - 分析服务：实时统计商品销量
    - 推荐系统：更新用户购买偏好

    框架自动处理：
    - 事件持久化（Outbox）
    - 事件发布（消息队列）
    - 事件追踪（event_id, occurred_at）
    """

    name: str = "order_created"

    # 订单基本信息
    order_id: str
    customer_id: str
    total: float
    item_count: int

    # 订单项详情 - 下游服务可以立即处理，无需额外查询
    items: list[dict]  # 每个 item 包含: product_id, product_name, quantity, unit_price, subtotal
