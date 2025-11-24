"""MockInventoryAdapter - Mock 库存适配器

用于开发和测试环境的模拟库存实现。
符合六边形架构：实现 IInventoryService Port。

特点：
- 内存存储库存数据
- 支持库存检查、预留、扣减、恢复
- 自动生成预留ID
- 默认所有产品库存充足
"""

from __future__ import annotations

import uuid

from contexts.ordering.domain.ports.services.i_inventory_service import (
    IInventoryService,
    InventoryItem,
    ReservationRequest,
    ReservationResult,
)


class MockInventoryAdapter(IInventoryService):
    """Mock 库存适配器（用于测试和开发）

    实现：IInventoryService (domain/ports/services/i_inventory_service.py)

    特性：
    - 内存管理库存
    - 默认所有产品库存 9999
    - 支持预留和扣减
    - 自动生成预留ID
    """

    def __init__(self, default_quantity: int = 9999):
        """初始化 Mock 库存适配器

        Args:
            default_quantity: 默认库存数量
        """
        self._default_quantity = default_quantity
        self._inventory: dict[str, InventoryItem] = {}  # 库存数据
        self._reservations: dict[str, ReservationRequest] = {}  # 预留记录

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
            f"📦 [MockInventory] Check availability: {product_id} - "
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
        if product_id not in self._inventory:
            # 如果不存在，创建默认库存
            self._inventory[product_id] = InventoryItem(
                product_id=product_id,
                available_quantity=self._default_quantity,
                reserved_quantity=0,
                total_quantity=self._default_quantity,
            )

        return self._inventory[product_id]

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
                f"⚠️ [MockInventory] Reservation failed: {reservation_id} - "
                f"Insufficient stock for: {', '.join(failed_items)}"
            )

            return ReservationResult(
                reservation_id=reservation_id,
                success=False,
                failed_items=failed_items,
                message=f"Insufficient stock for products: {', '.join(failed_items)}",
            )

        # 预留库存
        for product_id, quantity in request.items:
            inventory = self._inventory[product_id]

            # 更新库存
            self._inventory[product_id] = InventoryItem(
                product_id=product_id,
                available_quantity=inventory.available_quantity - quantity,
                reserved_quantity=inventory.reserved_quantity + quantity,
                total_quantity=inventory.total_quantity,
            )

        # 记录预留
        self._reservations[reservation_id] = request

        print(
            f"✅ [MockInventory] Reservation successful: {reservation_id} - "
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
            print(f"⚠️ [MockInventory] Release failed: Reservation {reservation_id} not found")
            return False

        request = self._reservations[reservation_id]

        # 释放库存
        for product_id, quantity in request.items:
            if product_id in self._inventory:
                inventory = self._inventory[product_id]

                self._inventory[product_id] = InventoryItem(
                    product_id=product_id,
                    available_quantity=inventory.available_quantity + quantity,
                    reserved_quantity=max(0, inventory.reserved_quantity - quantity),
                    total_quantity=inventory.total_quantity,
                )

        # 移除预留记录
        del self._reservations[reservation_id]

        print(f"♻️ [MockInventory] Reservation released: {reservation_id}")

        return True

    async def deduct_inventory(self, product_id: str, quantity: int) -> bool:
        """扣减库存

        Args:
            product_id: 产品ID
            quantity: 扣减数量

        Returns:
            bool: 是否成功扣减
        """
        inventory = await self.get_inventory(product_id)

        # 检查库存是否充足（从预留或可用中扣减）
        total_available = inventory.available_quantity + inventory.reserved_quantity

        if total_available < quantity:
            print(
                f"❌ [MockInventory] Deduct failed: {product_id} - "
                f"Insufficient stock (need: {quantity}, available: {total_available})"
            )
            return False

        # 优先从预留库存扣减
        reserved_deduct = min(quantity, inventory.reserved_quantity)
        available_deduct = quantity - reserved_deduct

        self._inventory[product_id] = InventoryItem(
            product_id=product_id,
            available_quantity=inventory.available_quantity - available_deduct,
            reserved_quantity=inventory.reserved_quantity - reserved_deduct,
            total_quantity=inventory.total_quantity - quantity,
        )

        print(
            f"➖ [MockInventory] Inventory deducted: {product_id} - "
            f"Quantity: {quantity}, Remaining: {self._inventory[product_id].total_quantity}"
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
        inventory = await self.get_inventory(product_id)

        self._inventory[product_id] = InventoryItem(
            product_id=product_id,
            available_quantity=inventory.available_quantity + quantity,
            reserved_quantity=inventory.reserved_quantity,
            total_quantity=inventory.total_quantity + quantity,
        )

        print(
            f"➕ [MockInventory] Inventory restored: {product_id} - "
            f"Quantity: {quantity}, Total: {self._inventory[product_id].total_quantity}"
        )

        return True

    # ============ 辅助方法 ============

    def get_all_inventory(self) -> dict[str, InventoryItem]:
        """获取所有库存（仅用于测试）"""
        return self._inventory.copy()

    def set_inventory(self, product_id: str, quantity: int):
        """设置库存（仅用于测试）"""
        self._inventory[product_id] = InventoryItem(
            product_id=product_id,
            available_quantity=quantity,
            reserved_quantity=0,
            total_quantity=quantity,
        )
        print(f"📝 [MockInventory] Inventory set: {product_id} = {quantity}")

    def clear_all(self):
        """清空所有数据（仅用于测试）"""
        self._inventory.clear()
        self._reservations.clear()
        print("🧹 [MockInventory] All inventory data cleared")
