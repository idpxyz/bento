"""IInventoryService - Secondary Port（被驱动端口）

库存服务接口，定义 Ordering Context 检查和扣减库存的契约。
符合六边形架构原则：Domain 层定义接口，Infrastructure 层实现。

Port vs Adapter:
- Port（本文件）: Domain 层定义的接口契约
- Adapter（infrastructure/adapters/）: 接口的具体技术实现

注意：
在 DDD 中，库存管理可能属于独立的 Inventory BC（库存上下文）。
如果库存逻辑复杂，建议创建独立的 BC 而不是通过 Service 调用。
此接口适用于简单的库存检查和扣减场景。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class InventoryItem:
    """库存项（值对象）"""

    product_id: str
    available_quantity: int  # 可用数量
    reserved_quantity: int = 0  # 已预留数量
    total_quantity: int = 0  # 总库存


@dataclass(frozen=True)
class ReservationRequest:
    """库存预留请求（值对象）"""

    order_id: str
    items: list[tuple[str, int]]  # [(product_id, quantity), ...]


@dataclass(frozen=True)
class ReservationResult:
    """库存预留结果（值对象）"""

    reservation_id: str
    success: bool
    failed_items: list[str] | None = None  # 失败的产品ID列表
    message: str = ""


class IInventoryService(ABC):
    """库存服务接口（Secondary Port - 被驱动端口）

    职责：
    1. 定义 Ordering BC 检查和管理库存的契约
    2. 隔离库存系统的变化（反腐败层）
    3. 支持依赖倒置（Domain 不依赖具体库存实现）

    实现方式由 Adapter 决定：
    - LocalInventoryAdapter: 本地数据库库存
    - InventoryServiceAdapter: 调用独立的库存服务
    - RedisInventoryAdapter: 基于 Redis 的库存
    - MockInventoryAdapter: 模拟库存（测试）

    库存管理策略：
    - 预留（Reserve）: 创建订单时预留库存，支付后扣减
    - 直接扣减（Deduct）: 创建订单直接扣减库存
    """

    @abstractmethod
    async def check_availability(self, product_id: str, quantity: int) -> bool:
        """检查库存是否充足

        Args:
            product_id: 产品ID
            quantity: 需要数量

        Returns:
            bool: 库存是否充足
        """
        pass

    @abstractmethod
    async def check_availability_batch(self, items: list[tuple[str, int]]) -> dict[str, bool]:
        """批量检查库存

        Args:
            items: [(product_id, quantity), ...]

        Returns:
            dict: {product_id: is_available, ...}
        """
        pass

    @abstractmethod
    async def get_inventory(self, product_id: str) -> InventoryItem:
        """获取库存信息

        Args:
            product_id: 产品ID

        Returns:
            InventoryItem: 库存信息
        """
        pass

    @abstractmethod
    async def reserve_inventory(self, request: ReservationRequest) -> ReservationResult:
        """预留库存

        用于订单创建时预留库存，支付后再扣减。
        如果支付失败或订单取消，需要释放预留。

        Args:
            request: 预留请求

        Returns:
            ReservationResult: 预留结果
        """
        pass

    @abstractmethod
    async def release_reservation(self, reservation_id: str) -> bool:
        """释放预留库存

        用于订单取消或支付失败时释放预留的库存。

        Args:
            reservation_id: 预留ID

        Returns:
            bool: 是否成功释放
        """
        pass

    @abstractmethod
    async def deduct_inventory(self, product_id: str, quantity: int) -> bool:
        """扣减库存

        直接扣减库存，用于支付成功后确认扣减。

        Args:
            product_id: 产品ID
            quantity: 扣减数量

        Returns:
            bool: 是否成功扣减
        """
        pass

    @abstractmethod
    async def restore_inventory(self, product_id: str, quantity: int) -> bool:
        """恢复库存

        用于退款或取消订单后恢复库存。

        Args:
            product_id: 产品ID
            quantity: 恢复数量

        Returns:
            bool: 是否成功恢复
        """
        pass
