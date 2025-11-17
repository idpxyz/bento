"""Order 聚合根"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from bento.domain.aggregate import AggregateRoot

from contexts.ordering.domain.orderitem import OrderItem


class OrderStatus(str, Enum):
    """订单状态"""

    PENDING = "pending"  # 待支付
    PAID = "paid"  # 已支付
    PROCESSING = "processing"  # 处理中
    SHIPPED = "shipped"  # 已发货
    DELIVERED = "delivered"  # 已送达
    CANCELLED = "cancelled"  # 已取消
    REFUNDED = "refunded"  # 已退款


@dataclass
class Order(AggregateRoot):
    """Order 聚合根

    订单是订单上下文的核心聚合根，包含订单项（OrderItem）。
    订单项作为聚合的一部分，不单独存在。

    业务规则：
    - 订单必须至少有一个订单项
    - 订单总额由所有订单项小计之和计算
    - 只有待支付订单可以取消
    - 只有已支付订单可以发货
    """

    id: str
    customer_id: str
    items: list[OrderItem] = field(default_factory=list)
    total: float = 0.0
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime | None = None
    paid_at: datetime | None = None
    shipped_at: datetime | None = None

    def __post_init__(self):
        super().__init__(id=self.id)
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        # 自动计算总额
        if self.items:
            self.total = self.calculate_total()

    def calculate_total(self) -> float:
        """计算订单总额"""
        return sum(item.subtotal for item in self.items)

    def add_item(self, product_id: str, product_name: str, quantity: int, unit_price: float):
        """添加订单项"""
        if quantity <= 0:
            raise ValueError("数量必须大于0")
        if unit_price < 0:
            raise ValueError("单价不能为负数")

        item = OrderItem(
            id=f"{self.id}-{len(self.items) + 1}",
            order_id=self.id,
            product_id=product_id,
            product_name=product_name,
            quantity=quantity,
            unit_price=unit_price,
        )
        self.items.append(item)
        self.total = self.calculate_total()

    def remove_item(self, product_id: str):
        """移除订单项"""
        if self.status != OrderStatus.PENDING:
            raise ValueError("只有待支付订单可以修改订单项")

        self.items = [item for item in self.items if item.product_id != product_id]
        if not self.items:
            raise ValueError("订单必须至少有一个商品")

        self.total = self.calculate_total()

    def confirm_payment(self):
        """确认支付"""
        if self.status != OrderStatus.PENDING:
            raise ValueError("只有待支付订单可以确认支付")

        if not self.items:
            raise ValueError("订单必须至少有一个商品")

        self.status = OrderStatus.PAID
        self.paid_at = datetime.utcnow()

        from contexts.ordering.domain.events.orderpaid_event import OrderPaidEvent

        self.add_event(
            OrderPaidEvent(
                aggregate_id=self.id,
                tenant_id="default",
                order_id=self.id,
                customer_id=self.customer_id,
                total=self.total,
                paid_at=self.paid_at,
            )
        )

    def ship(self, tracking_number: str | None = None):
        """发货"""
        if self.status != OrderStatus.PAID:
            raise ValueError("只有已支付订单可以发货")

        self.status = OrderStatus.SHIPPED
        self.shipped_at = datetime.utcnow()

        from contexts.ordering.domain.events.ordershipped_event import OrderShippedEvent

        self.add_event(
            OrderShippedEvent(
                aggregate_id=self.id,
                tenant_id="default",
                order_id=self.id,
                tracking_number=tracking_number,
                shipped_at=self.shipped_at,
            )
        )

    def deliver(self):
        """确认送达"""
        if self.status != OrderStatus.SHIPPED:
            raise ValueError("只有已发货订单可以确认送达")

        self.status = OrderStatus.DELIVERED

        from contexts.ordering.domain.events.orderdelivered_event import OrderDeliveredEvent

        self.add_event(
            OrderDeliveredEvent(
                aggregate_id=self.id,
                tenant_id="default",
                order_id=self.id,
                delivered_at=datetime.utcnow(),
            )
        )

    def cancel(self, reason: str):
        """取消订单"""
        if self.status not in [OrderStatus.PENDING, OrderStatus.PAID]:
            raise ValueError("只有待支付或已支付的订单可以取消")

        if self.status == OrderStatus.SHIPPED:
            raise ValueError("已发货的订单无法取消")

        old_status = self.status
        self.status = OrderStatus.CANCELLED

        from contexts.ordering.domain.events.ordercancelled_event import OrderCancelledEvent

        self.add_event(
            OrderCancelledEvent(
                aggregate_id=self.id,
                tenant_id="default",
                order_id=self.id,
                reason=reason,
                previous_status=old_status.value,
            )
        )
