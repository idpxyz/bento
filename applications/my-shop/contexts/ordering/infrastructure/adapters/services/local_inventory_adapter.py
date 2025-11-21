"""LocalInventoryAdapter - 本地数据库库存适配器

基于本地数据库的库存管理实现。
符合六边形架构：实现 IInventoryService Port。

特点：
- 使用 SQLAlchemy 管理库存
- 支持事务
- 支持库存预留和扣减
- 与 Catalog BC 的 Product 表集成
"""

from __future__ import annotations

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from contexts.catalog.infrastructure.models.product_po import ProductPO
from contexts.ordering.domain.ports.services.i_inventory_service import (
    IInventoryService,
    InventoryItem,
    ReservationRequest,
    ReservationResult,
)


class LocalInventoryAdapter(IInventoryService):
    """本地数据库库存适配器

    实现：IInventoryService (domain/ports/services/i_inventory_service.py)

    特性：
    - 直接查询 Catalog BC 的 Product 表
    - 使用数据库事务保证一致性
    - 支持库存预留（内存记录）
    - 支持库存扣减（更新数据库）

    注意：
    - 预留信息存储在内存中（生产环境应使用 Redis）
    - 跨 BC 访问数据表（仅读取和更新库存字段）
    """

    def __init__(self, session: AsyncSession):
        """初始化库存适配器

        Args:
            session: 数据库会话
        """
        self._session = session
        self._reservations: dict[str, ReservationRequest] = {}  # 内存预留记录

    async def check_availability(self, product_id: str, quantity: int) -> bool:
        """检查库存是否充足

        Args:
            product_id: 产品ID
            quantity: 需要数量

        Returns:
            bool: 库存是否充足
        """
        inventory = await self.get_inventory(product_id)
        is_available = inventory.available_quantity >= quantity

        print(
            f"📦 [LocalInventory] Check availability: {product_id} - "
            f"Need: {quantity}, Available: {inventory.available_quantity}, "
            f"Result: {'✅ OK' if is_available else '❌ Insufficient'}"
        )

        return is_available

    async def check_availability_batch(self, items: list[tuple[str, int]]) -> dict[str, bool]:
        """批量检查库存

        Args:
            items: [(product_id, quantity), ...]

        Returns:
            dict: {product_id: is_available, ...}
        """
        results = {}

        for product_id, quantity in items:
            results[product_id] = await self.check_availability(product_id, quantity)

        return results

    async def get_inventory(self, product_id: str) -> InventoryItem:
        """获取库存信息

        Args:
            product_id: 产品ID

        Returns:
            InventoryItem: 库存信息
        """
        # 查询产品库存
        stmt = select(ProductPO).where(ProductPO.id == product_id, ProductPO.deleted_at.is_(None))
        result = await self._session.execute(stmt)
        product = result.scalar_one_or_none()

        if not product:
            # 产品不存在，返回零库存
            return InventoryItem(
                product_id=product_id,
                available_quantity=0,
                reserved_quantity=0,
                total_quantity=0,
            )

        # 计算预留数量
        reserved_quantity = self._get_reserved_quantity(product_id)

        # 返回库存信息
        return InventoryItem(
            product_id=product_id,
            available_quantity=max(0, (product.stock or 0) - reserved_quantity),
            reserved_quantity=reserved_quantity,
            total_quantity=product.stock or 0,
        )

    async def reserve_inventory(self, request: ReservationRequest) -> ReservationResult:
        """预留库存

        Args:
            request: 预留请求

        Returns:
            ReservationResult: 预留结果
        """
        # 生成预留ID
        reservation_id = f"RSV_{uuid.uuid4().hex[:12].upper()}"

        failed_items = []

        # 检查所有商品库存
        for product_id, quantity in request.items:
            inventory = await self.get_inventory(product_id)

            if inventory.available_quantity < quantity:
                failed_items.append(product_id)

        # 如果有商品库存不足，返回失败
        if failed_items:
            print(
                f"⚠️ [LocalInventory] Reservation failed: {reservation_id} - "
                f"Insufficient stock for: {', '.join(failed_items)}"
            )

            return ReservationResult(
                reservation_id=reservation_id,
                success=False,
                failed_items=failed_items,
                message=f"Insufficient stock for products: {', '.join(failed_items)}",
            )

        # 记录预留（内存）
        self._reservations[reservation_id] = request

        print(
            f"✅ [LocalInventory] Reservation successful: {reservation_id} - "
            f"Order: {request.order_id}"
        )

        return ReservationResult(
            reservation_id=reservation_id,
            success=True,
            message="Inventory reserved successfully",
        )

    async def release_reservation(self, reservation_id: str) -> bool:
        """释放预留库存

        Args:
            reservation_id: 预留ID

        Returns:
            bool: 是否成功释放
        """
        if reservation_id not in self._reservations:
            print(f"⚠️ [LocalInventory] Release failed: Reservation {reservation_id} not found")
            return False

        # 移除预留记录
        del self._reservations[reservation_id]

        print(f"♻️ [LocalInventory] Reservation released: {reservation_id}")

        return True

    async def deduct_inventory(self, product_id: str, quantity: int) -> bool:
        """扣减库存

        Args:
            product_id: 产品ID
            quantity: 扣减数量

        Returns:
            bool: 是否成功扣减
        """
        # 查询当前库存
        stmt = select(ProductPO).where(ProductPO.id == product_id, ProductPO.deleted_at.is_(None))
        result = await self._session.execute(stmt)
        product = result.scalar_one_or_none()

        if not product:
            print(f"❌ [LocalInventory] Deduct failed: Product {product_id} not found")
            return False

        # 检查库存是否充足
        current_stock = product.stock or 0

        if current_stock < quantity:
            print(
                f"❌ [LocalInventory] Deduct failed: {product_id} - "
                f"Insufficient stock (need: {quantity}, available: {current_stock})"
            )
            return False

        # 扣减库存
        new_stock = current_stock - quantity

        update_stmt = update(ProductPO).where(ProductPO.id == product_id).values(stock=new_stock)

        await self._session.execute(update_stmt)
        await self._session.flush()

        print(
            f"➖ [LocalInventory] Inventory deducted: {product_id} - "
            f"Quantity: {quantity}, Remaining: {new_stock}"
        )

        return True

    async def restore_inventory(self, product_id: str, quantity: int) -> bool:
        """恢复库存

        Args:
            product_id: 产品ID
            quantity: 恢复数量

        Returns:
            bool: 是否成功恢复
        """
        # 查询当前库存
        stmt = select(ProductPO).where(ProductPO.id == product_id, ProductPO.deleted_at.is_(None))
        result = await self._session.execute(stmt)
        product = result.scalar_one_or_none()

        if not product:
            print(f"❌ [LocalInventory] Restore failed: Product {product_id} not found")
            return False

        # 恢复库存
        current_stock = product.stock or 0
        new_stock = current_stock + quantity

        update_stmt = update(ProductPO).where(ProductPO.id == product_id).values(stock=new_stock)

        await self._session.execute(update_stmt)
        await self._session.flush()

        print(
            f"➕ [LocalInventory] Inventory restored: {product_id} - "
            f"Quantity: {quantity}, Total: {new_stock}"
        )

        return True

    # ============ 辅助方法 ============

    def _get_reserved_quantity(self, product_id: str) -> int:
        """获取产品的总预留数量

        Args:
            product_id: 产品ID

        Returns:
            int: 预留数量
        """
        total_reserved = 0

        for reservation in self._reservations.values():
            for pid, qty in reservation.items:
                if pid == product_id:
                    total_reserved += qty

        return total_reserved

    def clear_reservations(self):
        """清空所有预留记录（仅用于测试）"""
        self._reservations.clear()
        print("🧹 [LocalInventory] All reservations cleared")
