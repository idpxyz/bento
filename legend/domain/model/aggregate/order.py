# 示例
from typing import Dict, List

from idp.framework.domain.model.aggregate.base import AggregateRoot
from idp.framework.domain.model.entity.base import Entity


class OrderItem(Entity):
    """订单商品"""
    product_id: str
    quantity: int


class DomainError(Exception):
    """领域错误"""
    pass


class Order(AggregateRoot):
    customer_id: str
    customer_name: str
    address: str
    items: List[OrderItem] = []

    async def add(self, product_id: str, quantity: int) -> None:
        """添加商品"""
        if len(self.items) >= 100:
            raise DomainError("订单商品数量不能超过100")
        self.items.append(OrderItem(product_id, quantity))
        self.raise_event(OrderItemAdded(self.id, product_id, quantity))

    async def remove(self, product_id: str) -> None:
        """移除商品"""
        self.items = [
            item for item in self.items if item.product_id != product_id]

    def place(self, items: List[OrderItem]):
        # 业务逻辑
        self._items = items
        self._status = OrderStatus.PLACED

        # 触发领域事件
        self.raise_event(DomainEvent(
            aggregate_type="Order",
            aggregate_id=self.id,
            event_type="OrderPlaced",
            payload={
                "items": [{"id": item.id, "quantity": item.quantity} for item in items]
            }
        ))


async def place_order(order_id: str, items: List[Dict]) -> None:
    async with SqlAlchemyUnitOfWork(session) as uow:
        # 通过仓储获取聚合根
        order = await order_repository.get_by_id(order_id)

        # 执行领域操作
        order.place([OrderItem(**item) for item in items])

        # 保存更改 - 这会自动处理事件
        await uow.commit()
