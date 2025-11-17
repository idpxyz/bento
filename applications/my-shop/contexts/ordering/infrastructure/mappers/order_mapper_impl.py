"""Order Mapper 实现 - 处理 Order + OrderItem 聚合映射"""

from datetime import datetime

from contexts.ordering.domain.order import Order, OrderStatus
from contexts.ordering.domain.orderitem import OrderItem
from contexts.ordering.infrastructure.models.order_po import OrderPO
from contexts.ordering.infrastructure.models.orderitem_po import OrderItemPO


class OrderMapper:
    """Order Mapper - 手动实现聚合映射
    
    由于 Order 包含 OrderItem 集合，需要自定义映射逻辑。
    """
    
    def map(self, domain: Order) -> OrderPO:
        """领域对象 -> 持久化对象"""
        po = OrderPO(
            id=domain.id,
            customer_id=domain.customer_id,
            total=domain.total,
            status=domain.status.value if isinstance(domain.status, OrderStatus) else domain.status,
            paid_at=domain.paid_at,
            shipped_at=domain.shipped_at,
        )
        # 注意：OrderItem 需要单独保存，通过 Repository 处理
        return po
    
    def map_reverse(self, po: OrderPO) -> Order:
        """持久化对象 -> 领域对象"""
        # 注意：这里不包含 items，需要通过 Repository 加载
        order = Order(
            id=po.id,
            customer_id=po.customer_id,
            items=[],  # 稍后填充
            total=po.total,
            status=OrderStatus(po.status),
            created_at=po.created_at,
            paid_at=po.paid_at,
            shipped_at=po.shipped_at,
        )
        return order
    
    def map_item(self, item: OrderItem) -> OrderItemPO:
        """OrderItem -> OrderItemPO"""
        return OrderItemPO(
            id=item.id,
            order_id=item.order_id,
            product_id=item.product_id,
            product_name=item.product_name,
            quantity=item.quantity,
            unit_price=item.unit_price,
        )
    
    def map_item_reverse(self, po: OrderItemPO) -> OrderItem:
        """OrderItemPO -> OrderItem"""
        return OrderItem(
            id=po.id,
            order_id=po.order_id,
            product_id=po.product_id,
            product_name=po.product_name,
            quantity=po.quantity,
            unit_price=po.unit_price,
        )
