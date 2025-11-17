"""Order Repository 实现 - 使用 Bento RepositoryAdapter"""

from __future__ import annotations

from bento.infrastructure.repository import RepositoryAdapter
from bento.persistence.interceptor import create_default_chain
from bento.persistence.repository.sqlalchemy import BaseRepository
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from contexts.ordering.domain.order import Order
from contexts.ordering.infrastructure.mappers.order_mapper_impl import (
    OrderItemMapper,
    OrderMapper,
)
from contexts.ordering.infrastructure.models.order_po import OrderPO
from contexts.ordering.infrastructure.models.orderitem_po import OrderItemPO


class OrderRepository(RepositoryAdapter[Order, OrderPO, str]):
    """Order Repository - 使用 Bento RepositoryAdapter

    提供：
    - 自动 CRUD 操作（通过 RepositoryAdapter）
    - 聚合根映射（Order <-> OrderPO）
    - 审计、软删除、乐观锁（通过 Interceptor）
    - 聚合级联处理（Order + OrderItems）

    框架特性：
    - 自动审计字段（created_at, updated_at, created_by, updated_by）
    - 乐观锁（version 字段）
    - 软删除支持
    - UnitOfWork 集成（事件收集）
    """

    def __init__(self, session: AsyncSession, actor: str = "system"):
        # 创建映射器
        order_mapper = OrderMapper()
        self.item_mapper = OrderItemMapper()

        # 创建基础仓储 + 拦截器链
        base_repo = BaseRepository(
            session=session,
            po_type=OrderPO,
            actor=actor,
            interceptor_chain=create_default_chain(actor),
        )

        # 初始化适配器
        super().__init__(repository=base_repo, mapper=order_mapper)

        self.session = session
        self.actor = actor

    async def get(self, order_id: str) -> Order | None:
        """获取 Order + OrderItems（聚合加载）

        步骤：
        1. 加载 Order（通过 RepositoryAdapter）
        2. 加载 OrderItems
        3. 组装聚合
        """
        # 1. 加载 Order（使用父类方法）
        order = await super().get(order_id)
        if not order:
            return None

        # 2. 加载 OrderItems
        result = await self.session.execute(
            select(OrderItemPO).where(OrderItemPO.order_id == order_id)
        )
        item_pos = result.scalars().all()

        # 3. 组装聚合
        order.items = [self.item_mapper.map_reverse(item_po) for item_po in item_pos]

        # 重新计算 total（确保一致性）
        order.total = order.calculate_total()

        return order

    # ============ 聚合级联操作 ===========

    async def save(self, order: Order) -> None:
        """保存 Order + OrderItems（聚合级联）

        步骤：
        1. 保存 Order（通过 RepositoryAdapter，自动处理审计字段）
        2. 删除旧的 OrderItems
        3. 保存新的 OrderItems（通过 BaseRepository，自动审计）
        """
        # 1. 保存 Order（使用父类方法，自动处理审计字段）
        await super().save(order)

        # 2. 删除旧的 OrderItems
        await self.session.execute(delete(OrderItemPO).where(OrderItemPO.order_id == order.id))

        # 3. 保存新的 OrderItems（使用 BaseRepository 自动处理审计）
        item_base_repo = BaseRepository(
            session=self.session,
            po_type=OrderItemPO,
            actor=self.actor,
            interceptor_chain=create_default_chain(self.actor),
        )

        for item in order.items:
            item_po = self.item_mapper.map(item)
            await item_base_repo.create_po(item_po)

        # ✅ Automatically track aggregate for event collection
        if self._uow:
            self._uow.track(order)

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
        """列表查询（不包含 items）

        如需加载 items，请使用 get() 逐个加载。
        """
        # 使用父类方法
        return await super().list()

    # ============ 自定义查询方法 ===========

    async def find_by_customer(self, customer_id: str) -> list[Order]:
        """根据客户ID查询订单列表（不包含items）。"""
        result = await self.session.execute(
            select(OrderPO).where(OrderPO.customer_id == customer_id)
        )
        pos = result.scalars().all()
        return [self.mapper.map_reverse(po) for po in pos]
