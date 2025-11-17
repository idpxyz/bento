"""Order Repository 实现 - 处理 Order + OrderItem 聚合持久化"""

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from contexts.ordering.domain.order import Order
from contexts.ordering.infrastructure.mappers.order_mapper_impl import OrderMapper
from contexts.ordering.infrastructure.models.order_po import OrderPO
from contexts.ordering.infrastructure.models.orderitem_po import OrderItemPO


class OrderRepository:
    """Order Repository - 手动实现聚合仓储

    处理 Order + OrderItem 的完整聚合持久化。
    由于 Order 是聚合根，包含 OrderItem 集合，需要：
    1. 保存 Order 时级联保存所有 OrderItem
    2. 查询 Order 时加载所有 OrderItem
    3. 删除 Order 时级联删除所有 OrderItem
    """

    def __init__(self, session: AsyncSession, actor: str = "system"):
        self.session = session
        self.actor = actor
        self.mapper = OrderMapper()

    async def get(self, order_id: str) -> Order | None:
        """根据 ID 获取 Order 聚合（包含 OrderItem）"""
        # 1. 查询 OrderPO
        result = await self.session.execute(select(OrderPO).where(OrderPO.id == order_id))
        order_po = result.scalar_one_or_none()

        if not order_po:
            return None

        # 2. 查询所有 OrderItemPO
        result = await self.session.execute(
            select(OrderItemPO).where(OrderItemPO.order_id == order_id)
        )
        item_pos = result.scalars().all()

        # 3. 映射为领域对象
        order = self.mapper.map_reverse(order_po)
        order.items = [self.mapper.map_item_reverse(item_po) for item_po in item_pos]

        # 重新计算 total（确保一致性）
        order.total = order.calculate_total()

        return order

    async def save(self, order: Order) -> None:
        """保存 Order 聚合（级联保存 OrderItem）"""
        # 1. 映射并保存 OrderPO
        order_po = self.mapper.map(order)

        # 检查是否已存在
        existing = await self.session.get(OrderPO, order.id)
        if existing:
            # 更新
            for key, value in order_po.__dict__.items():
                if not key.startswith("_"):
                    setattr(existing, key, value)
        else:
            # 新增
            self.session.add(order_po)

        # 2. 删除旧的 OrderItem（简单策略：全删全插）
        await self.session.execute(delete(OrderItemPO).where(OrderItemPO.order_id == order.id))

        # 3. 插入新的 OrderItem
        for item in order.items:
            item_po = self.mapper.map_item(item)
            self.session.add(item_po)

        # 4. 刷新到数据库
        await self.session.flush()

    async def delete(self, order: Order) -> None:
        """删除 Order 聚合（软删除）"""
        order_po = await self.session.get(OrderPO, order.id)
        if order_po:
            # 软删除 Order
            await self.session.delete(order_po)

            # 删除所有 OrderItem（硬删除，因为它们不需要软删除）
            await self.session.execute(delete(OrderItemPO).where(OrderItemPO.order_id == order.id))

        await self.session.flush()

    async def list(self) -> list[Order]:
        """列出所有订单（包含 OrderItem）"""
        # 1. 查询所有 OrderPO
        result = await self.session.execute(select(OrderPO))
        order_pos = result.scalars().all()

        # 2. 查询所有 OrderItemPO
        result = await self.session.execute(select(OrderItemPO))
        all_item_pos = result.scalars().all()

        # 3. 按 order_id 分组
        items_by_order = {}
        for item_po in all_item_pos:
            if item_po.order_id not in items_by_order:
                items_by_order[item_po.order_id] = []
            items_by_order[item_po.order_id].append(item_po)

        # 4. 组装聚合
        orders = []
        for order_po in order_pos:
            order = self.mapper.map_reverse(order_po)
            item_pos = items_by_order.get(order_po.id, [])
            order.items = [self.mapper.map_item_reverse(item_po) for item_po in item_pos]
            order.total = order.calculate_total()
            orders.append(order)

        return orders

    async def find_by_customer(self, customer_id: str) -> list[Order]:
        """根据客户ID查询订单"""
        result = await self.session.execute(
            select(OrderPO).where(OrderPO.customer_id == customer_id)
        )
        order_pos = result.scalars().all()

        orders = []
        for order_po in order_pos:
            order = await self.get(order_po.id)
            if order:
                orders.append(order)

        return orders
