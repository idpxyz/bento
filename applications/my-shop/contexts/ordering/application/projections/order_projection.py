"""Order Projection - P3 高级特性：将写模型投影到读模型"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from contexts.ordering.domain.events.ordercreated_event import OrderCreated
from contexts.ordering.domain.events.orderpaid_event import OrderPaidEvent
from contexts.ordering.domain.events.ordershipped_event import OrderShippedEvent
from contexts.ordering.infrastructure.models.order_po import OrderPO
from contexts.ordering.infrastructure.models.orderitem_po import OrderItemPO
from contexts.ordering.infrastructure.models.read_models.order_read_model import (
    OrderReadModel,
)


class OrderProjection:
    """将写模型投影到读模型

    P3 高级特性：CQRS 投影

    职责：
    - 监听领域事件
    - 更新读模型
    - 保持数据同步
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def handle_order_created(self, event: OrderCreated) -> None:
        """订单创建事件 → 创建读模型

        Args:
            event: OrderCreated 事件
        """
        # 1. 从写模型获取数据
        result = await self.session.execute(select(OrderPO).where(OrderPO.id == event.order_id))
        order_po = result.scalar_one_or_none()

        if not order_po:
            return

        # 2. 获取订单项
        result = await self.session.execute(
            select(OrderItemPO).where(OrderItemPO.order_id == event.order_id)
        )
        item_pos = result.scalars().all()

        # 3. 计算衍生字段
        total_amount = sum(item.quantity * item.unit_price for item in item_pos)
        items_count = len(item_pos)

        # 4. 创建读模型
        read_model = OrderReadModel(
            id=order_po.id,
            customer_id=order_po.customer_id,
            status=order_po.status,
            total_amount=total_amount,  # 预计算
            items_count=items_count,  # 预计算
            created_at=order_po.created_at,
            paid_at=order_po.paid_at,
            shipped_at=order_po.shipped_at,
        )

        self.session.add(read_model)
        await self.session.flush()

    async def handle_order_paid(self, event: OrderPaidEvent) -> None:
        """订单支付事件 → 更新读模型

        Args:
            event: OrderPaid 事件
        """
        result = await self.session.execute(
            select(OrderReadModel).where(OrderReadModel.id == event.order_id)
        )
        read_model = result.scalar_one_or_none()

        if read_model:
            read_model.status = "paid"
            read_model.paid_at = event.paid_at
            await self.session.flush()

    async def handle_order_shipped(self, event: OrderShippedEvent) -> None:
        """订单发货事件 → 更新读模型

        Args:
            event: OrderShipped 事件
        """
        result = await self.session.execute(
            select(OrderReadModel).where(OrderReadModel.id == event.order_id)
        )
        read_model = result.scalar_one_or_none()

        if read_model:
            read_model.status = "shipped"
            read_model.shipped_at = event.shipped_at
            await self.session.flush()
