"""完整示例：如何使用 Persistence Mixins + Interceptor.

这个示例展示了：
1. 使用不同的 Mixin 定义 PO
2. 配置 Repository + Interceptor
3. CRUD 操作中的自动字段填充
4. Domain Entity 与 PO 的分离
"""

from bento.persistence.po.mixins import (
    AuditFieldsMixin,
    FullAuditMixin,
    OptimisticLockFieldMixin,
)
from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# ============== 1. 定义基础设施组件 ==============


# SQLAlchemy Base
class Base(DeclarativeBase):
    """SQLAlchemy 声明基类"""

    pass


# ============== 2. 示例 1：使用 FullAuditMixin（推荐） ==============
class OrderPO(Base, FullAuditMixin):
    """订单 PO - 使用完整审计功能

    包含所有审计字段：
    - created_at, updated_at, created_by, updated_by (审计)
    - deleted_at, deleted_by (软删除)
    - version (乐观锁)
    """

    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    customer_id: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    total_amount: Mapped[int] = mapped_column(nullable=False)


# ============== 3. 示例 2：按需组合 Mixin ==============


class ProductPO(Base, AuditFieldsMixin, OptimisticLockFieldMixin):
    """产品 PO - 只使用审计+乐观锁，不需要软删除

    产品数据可以直接物理删除，不需要软删除功能
    """

    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    price: Mapped[int] = mapped_column(nullable=False)


# ============== 4. 示例 3：最小化 Mixin ==============
class LogPO(Base, AuditFieldsMixin):
    """日志 PO - 只需要创建时间，不需要更新/删除/版本控制

    日志记录是只写的，不会更新或删除
    """

    __tablename__ = "logs"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    message: Mapped[str] = mapped_column(String(1000), nullable=False)
    level: Mapped[str] = mapped_column(String(20), nullable=False)


# ============== 5. Domain Entity（纯净的领域模型）==============


class Order:
    """订单领域实体 - 不包含任何技术字段

    注意：
    - 没有 created_at, updated_at 等技术字段
    - 只关注业务逻辑和规则
    - 与持久化机制完全解耦
    """

    def __init__(self, order_id: str, customer_id: str):
        self.id = order_id
        self.customer_id = customer_id
        self.status = "pending"
        self.total_amount = 0
        self._items = []

    def add_item(self, product_id: str, quantity: int, price: int) -> None:
        """添加订单项（业务逻辑）"""
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        self._items.append({"product_id": product_id, "quantity": quantity, "price": price})
        self.total_amount += quantity * price

    def place_order(self) -> None:
        """下单（业务逻辑）"""
        if not self._items:
            raise ValueError("Cannot place empty order")
        if self.status != "pending":
            raise ValueError(f"Cannot place order in status: {self.status}")
        self.status = "placed"

    def cancel(self) -> None:
        """取消订单（业务逻辑）"""
        if self.status not in ["pending", "placed"]:
            raise ValueError(f"Cannot cancel order in status: {self.status}")
        self.status = "cancelled"


# ============== 6. Mapper（Domain ↔ PO 转换）==============


class OrderMapper:
    """订单映射器 - 负责 Domain Entity 和 PO 之间的转换

    关键职责：
    - 过滤掉技术字段（created_at, updated_at 等）
    - 确保 Domain Entity 的纯净性
    """

    @staticmethod
    def to_persistence(domain: Order) -> OrderPO:
        """Domain → PO：只映射业务字段"""
        return OrderPO(
            id=domain.id,
            customer_id=domain.customer_id,
            status=domain.status,
            total_amount=domain.total_amount,
            # ❌ 不设置 created_at, updated_at, created_by, updated_by, version
            # ✅ 这些由 Interceptor 自动填充
        )

    @staticmethod
    def to_domain(po: OrderPO) -> Order:
        """PO → Domain：过滤掉技术字段"""
        order = Order(order_id=po.id, customer_id=po.customer_id)
        order.status = po.status
        order.total_amount = po.total_amount
        # ❌ 不传递 created_at, updated_at 等技术字段
        # ✅ Domain Entity 不需要知道这些
        return order


# ============== 7. 使用示例（伪代码）==============


async def example_usage():
    """完整使用流程示例

    注意：这是伪代码，实际使用需要配置 SQLAlchemy session
    """
    from bento.persistence.interceptor import create_default_chain
    from bento.persistence.repository import BaseRepository

    # 假设已有 session
    session = None  # type: ignore  # AsyncSession instance (伪代码)

    # ============== 创建 Repository ==============
    order_repo = BaseRepository(
        session=session,  # type: ignore[arg-type]
        po_type=OrderPO,
        interceptor_chain=create_default_chain(actor="user-123"),
    )

    # ============== 场景 1：创建订单 ==============
    print("\n=== 场景 1：创建订单 ===")

    # 1. 创建 Domain Entity（业务逻辑层）
    order = Order(order_id="order-001", customer_id="cust-001")
    order.add_item(product_id="prod-1", quantity=2, price=100)
    order.add_item(product_id="prod-2", quantity=1, price=200)
    order.place_order()

    # 2. 转换为 PO
    order_po = OrderMapper.to_persistence(order)

    # 3. 保存到数据库（Interceptor 自动填充字段）
    await order_repo.create_po(order_po)

    # ✅ 自动填充的字段：
    print(f"Created at: {order_po.created_at}")  # 2024-01-01 10:00:00
    print(f"Created by: {order_po.created_by}")  # "user-123"
    print(f"Updated at: {order_po.updated_at}")  # 2024-01-01 10:00:00
    print(f"Updated by: {order_po.updated_by}")  # "user-123"
    print(f"Version: {order_po.version}")  # 1

    # ============== 场景 2：更新订单 ==============
    print("\n=== 场景 2：更新订单 ===")

    # 1. 从数据库读取
    order_po = await order_repo.get_po_by_id("order-001")
    if not order_po:
        return
    print(f"Current version: {order_po.version}")  # 1

    # 2. 转换为 Domain Entity
    order = OrderMapper.to_domain(order_po)

    # 3. 执行业务逻辑
    order.cancel()

    # 4. 转换回 PO 并更新
    updated_po = OrderMapper.to_persistence(order)
    updated_po.version = order_po.version  # 保留版本号
    await order_repo.update_po(updated_po)

    # ✅ 自动更新的字段：
    print(f"Updated at: {updated_po.updated_at}")  # 2024-01-01 10:05:00 (更新)
    print(f"Updated by: {updated_po.updated_by}")  # "user-123"
    print(f"Version: {updated_po.version}")  # 2 (递增)
    print(f"Created at: {updated_po.created_at}")  # 2024-01-01 10:00:00 (不变)
    print(f"Created by: {updated_po.created_by}")  # "user-123" (不变)

    # ============== 场景 3：软删除订单 ==============
    print("\n=== 场景 3：软删除订单 ===")

    order_po = await order_repo.get_po_by_id("order-001")
    if not order_po:
        return
    await order_repo.delete_po(order_po)

    # ✅ 自动设置的字段：
    print(f"Deleted at: {order_po.deleted_at}")  # 2024-01-01 10:10:00
    print(f"Deleted by: {order_po.deleted_by}")  # "user-123"
    print(f"Is deleted: {order_po.is_deleted}")  # True
    print("❌ 数据库记录仍然存在（逻辑删除）")

    # ============== 场景 4：乐观锁冲突 ==============
    print("\n=== 场景 4：乐观锁并发冲突 ===")

    # 模拟并发场景
    # 线程 A 读取
    order_a = await order_repo.get_po_by_id("order-002")
    if not order_a:
        return
    print(f"Thread A - version: {order_a.version}")  # 1

    # 线程 B 读取
    order_b = await order_repo.get_po_by_id("order-002")
    if not order_b:
        return
    print(f"Thread B - version: {order_b.version}")  # 1

    # 线程 A 更新成功
    order_a.status = "shipped"
    await order_repo.update_po(order_a)
    print(f"Thread A - updated, new version: {order_a.version}")  # 2

    # 线程 B 更新失败（版本号冲突）
    try:
        order_b.status = "cancelled"
        await order_repo.update_po(order_b)  # version 仍然是 1
    except Exception as e:
        print(f"❌ Thread B - OptimisticLockException: {e}")


# ============== 8. 关键要点总结 ==============

"""
✅ 最佳实践：

1. PO 层（Persistence Object）：
   - 使用 Mixin 定义技术字段（created_at, updated_at, etc.）
   - 继承 FullAuditMixin 或按需组合 Mixin
   - 包含所有数据库相关的字段和配置

2. Domain 层（Domain Entity）：
   - 保持纯净，不包含任何技术字段
   - 只关注业务逻辑和规则
   - 完全与持久化机制解耦

3. Mapper 层：
   - 负责 Domain ↔ PO 的转换
   - 过滤掉技术字段，不传递给 Domain
   - 确保两层的隔离

4. Repository + Interceptor：
   - Repository 使用 BaseRepository
   - 配置 InterceptorChain
   - 自动处理所有技术字段的填充

5. 架构分层：
   Domain (Order)           ← 纯业务逻辑，无技术字段
        ↕ Mapper            ← 转换边界，过滤技术字段
   Persistence (OrderPO)    ← 包含技术字段（通过 Mixin）
        ↓ Interceptor       ← 自动填充字段值
   Database                 ← 持久化存储

❌ 常见错误：

1. ❌ 在 Domain Entity 上添加 created_at 等技术字段
2. ❌ 在 Domain 层导入 Mixin
3. ❌ 手动设置 created_at, updated_at 的值
4. ❌ 在业务逻辑中依赖技术字段

🎯 核心原则：

技术关注点（审计、软删除、版本控制）完全由基础设施层处理，
业务层（Domain）保持纯净，符合六边形架构的依赖倒置原则。
"""

if __name__ == "__main__":

    # asyncio.run(example_usage())
    print(__doc__)
    print("\n" + "=" * 60)
    print("✅ Persistence Mixins 已成功创建！")
    print("=" * 60)
    print("\n包含以下 Mixin：")
    print("  1. AuditFieldsMixin          - 审计字段")
    print("  2. SoftDeleteFieldsMixin     - 软删除字段")
    print("  3. OptimisticLockFieldMixin  - 乐观锁字段")
    print("  4. FullAuditMixin            - 完整功能（推荐）")
    print("\n使用方式：")
    print("  from bento.persistence import FullAuditMixin")
    print("  class MyPO(Base, FullAuditMixin): ...")
