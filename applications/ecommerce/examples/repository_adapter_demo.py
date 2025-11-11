#!/usr/bin/env python3
"""Repository Adapter Demo - Legend-style Repository

演示如何使用 RepositoryAdapter 实现类似 Legend 的 Repository：
- ✅ 继承即拥有所有 CRUD 方法
- ✅ 只需定义特殊查询
- ✅ 代码量减少 67%
"""

import asyncio
import sys
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from applications.ecommerce.modules.order.domain.order import Order
from applications.ecommerce.modules.order.persistence import OrderRepository
from bento.persistence import Base
from bento.core.ids import ID
from bento.infrastructure.database import init_database
from bento.persistence.specification import PageParams

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))


async def setup_database():
    """Setup in-memory database for demo"""
    # Import models to register them with Base
    from applications.ecommerce.modules.order.persistence.models import (  # noqa: F401
        OrderItemModel,
        OrderModel,
    )

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    await init_database(engine, Base, check_tables=False)
    return engine


async def get_session(engine):
    """Get async session"""
    async with AsyncSession(engine) as session:
        yield session


async def demo_basic_crud():
    """Demo 1: Basic CRUD operations (inherited from RepositoryAdapter)"""
    print("\n" + "=" * 60)
    print("Demo 1: 基础 CRUD 操作（自动继承）")
    print("=" * 60)

    engine = await setup_database()
    session_gen = get_session(engine)
    session = await anext(session_gen)

    try:
        # Initialize repository
        repo = OrderRepository(session, actor="demo@example.com")

        # 1. Create orders
        print("\n✅ 1. 创建订单（使用继承的 save 方法）")
        order1 = Order(
            order_id=ID("order-001"),
            customer_id=ID("cust-001"),
        )
        order1.add_item(
            product_id=ID("prod-001"),
            product_name="iPhone 15 Pro",
            quantity=1,
            unit_price=999.99,
        )

        order2 = Order(
            order_id=ID("order-002"),
            customer_id=ID("cust-001"),
        )
        order2.add_item(
            product_id=ID("prod-002"),
            product_name="MacBook Pro",
            quantity=1,
            unit_price=2499.99,
        )
        order2.pay()

        await repo.save(order1)  # ✅ Inherited method
        await repo.save(order2)  # ✅ Inherited method
        await session.commit()

        print(f"   Created order 1: {order1.id.value} (${order1.total_amount})")
        print(f"   Created order 2: {order2.id.value} (${order2.total_amount})")

        # 2. Get by ID
        print("\n✅ 2. 按 ID 查询（使用继承的 get 方法）")
        fetched_order = await repo.get(ID(order1.id.value))  # ✅ Inherited method
        if fetched_order:
            print(f"   Found: {fetched_order.id.value}")
            print(f"   Status: {fetched_order.status.value}")
            print(f"   Amount: ${fetched_order.total_amount}")

        # 3. List all
        print("\n✅ 3. 列出所有订单（使用继承的 list 方法）")
        all_orders = await repo.list()  # ✅ Inherited method
        print(f"   Total orders: {len(all_orders)}")
        for order in all_orders:
            print(
                f"   - {order.id.value}: {order.status.value} (${order.total_amount})"
            )

    finally:
        await anext(session_gen, None)
        await engine.dispose()


async def demo_custom_queries():
    """Demo 2: Custom query methods (only define what you need)"""
    print("\n" + "=" * 60)
    print("Demo 2: 自定义查询（只定义特殊查询）")
    print("=" * 60)

    engine = await setup_database()
    session_gen = get_session(engine)
    session = await anext(session_gen)

    try:
        repo = OrderRepository(session, actor="demo@example.com")

        # Create test data
        orders = []
        for i in range(5):
            order = Order(
                order_id=ID(f"order-{100+i}"),
                customer_id=ID(f"cust-{i % 2 + 1}"),  # cust-1 or cust-2
            )
            order.add_item(
                product_id=ID(f"prod-{i}"),
                product_name=f"Product {i}",
                quantity=1,
                unit_price=float((i + 1) * 100),
            )
            if i % 2 != 0:  # Pay odd-numbered orders
                order.pay()
            orders.append(order)

        await repo.save_all(orders)  # ✅ Inherited batch method
        await session.commit()

        print(f"\n✅ Created {len(orders)} test orders")

        # Custom query 1: Find unpaid
        print("\n✅ 1. 查找未支付订单（自定义方法）")
        unpaid_orders = await repo.find_unpaid()  # ✅ Custom method
        print(f"   Unpaid orders: {len(unpaid_orders)}")
        for order in unpaid_orders:
            print(f"   - {order.id.value}: ${order.total_amount}")

        # Custom query 2: Find by customer
        print("\n✅ 2. 按客户查询（自定义方法）")
        customer_orders = await repo.find_by_customer(
            ID("cust-1")
        )  # ✅ Custom method
        print(f"   Customer cust-1 orders: {len(customer_orders)}")

        # Custom query 3: Find high value
        print("\n✅ 3. 查找高价值订单（自定义方法）")
        vip_orders = await repo.find_high_value(min_amount=300.0)  # ✅ Custom method
        print(f"   High-value orders (>= $300): {len(vip_orders)}")
        for order in vip_orders:
            print(f"   - {order.id.value}: ${order.total_amount}")

        # Custom query 4: Find by status
        print("\n✅ 4. 按状态查询（自定义方法）")
        paid_orders = await repo.find_by_status("paid")  # ✅ Custom method
        print(f"   Paid orders: {len(paid_orders)}")

        # Custom query 5: Count by status
        print("\n✅ 5. 统计订单数量（自定义方法）")
        pending_count = await repo.count_by_status("pending")  # ✅ Custom method
        paid_count = await repo.count_by_status("paid")  # ✅ Custom method
        print(f"   Pending: {pending_count}")
        print(f"   Paid: {paid_count}")

    finally:
        await anext(session_gen, None)
        await engine.dispose()


async def demo_specification_queries():
    """Demo 3: Specification-based queries (inherited methods)"""
    print("\n" + "=" * 60)
    print("Demo 3: Specification 查询（继承的方法）")
    print("=" * 60)

    engine = await setup_database()
    session_gen = get_session(engine)
    session = await anext(session_gen)

    try:
        repo = OrderRepository(session, actor="demo@example.com")

        # Create test data
        for i in range(20):
            order = Order(
                order_id=ID(f"order-{200+i}"),
                customer_id=ID("cust-001"),
            )
            order.add_item(
                product_id=ID(f"prod-{i}"),
                product_name=f"Product {i}",
                quantity=1,
                unit_price=float((i + 1) * 50),
            )
            if i < 10:  # Pay first 10 orders
                order.pay()
            await repo.save(order)

        await session.commit()
        print("\n✅ Created 20 test orders")

        # 1. Dynamic query with build_query_spec
        print("\n✅ 1. 动态查询（使用 build_query_spec helper）")
        spec = repo.build_query_spec(
            customer_id=ID("cust-001"), status="paid", min_amount=200.0
        )
        results = await repo.list(spec)  # ✅ Inherited method
        print(f"   Results: {len(results)} orders")
        print("   (customer=cust-001, status=paid, amount>=200)")

        # 2. Pagination
        print("\n✅ 2. 分页查询（使用继承的 find_page 方法）")
        spec = repo.build_query_spec(customer_id=ID("cust-001"))
        page = await repo.find_page(spec, PageParams(page=1, size=5))  # ✅ Inherited
        print(f"   Page 1 of {page.total_pages}")
        print(f"   Showing {len(page.items)} of {page.total} total")
        print(f"   Has next: {page.has_next}")

        # 3. Count
        print("\n✅ 3. 统计查询（使用继承的 count 方法）")
        spec = repo.build_query_spec(status="paid")
        count = await repo.count(spec)  # ✅ Inherited method
        print(f"   Paid orders count: {count}")

        # 4. Exists
        print("\n✅ 4. 存在性检查（使用继承的 exists 方法）")
        has_orders = await repo.has_customer_orders(ID("cust-001"))  # Custom + exists
        print(f"   Customer has orders: {has_orders}")

    finally:
        await anext(session_gen, None)
        await engine.dispose()


async def demo_comparison():
    """Demo 4: Code comparison (V3 vs V4)"""
    print("\n" + "=" * 60)
    print("Demo 4: 代码对比（V3 手动实现 vs V4 RepositoryAdapter）")
    print("=" * 60)

    print("\n【V3 - 手动实现】(~150 行)")
    print("=" * 60)
    print(
        """
class OrderRepositoryWithInterceptors:
    def __init__(self, session, actor):
        self._base_repo = BaseRepository(...)
        self._mapper = OrderMapper()

    # ❌ 需要手动实现每个方法
    async def save(self, order):
        po = self._mapper.map(order)
        await self._base_repo.create_po(po)

    async def find_by_id(self, order_id):
        po = await self._base_repo.get_po_by_id(order_id.value)
        return self._mapper.map_reverse(po) if po else None

    async def delete(self, order):
        po = self._mapper.map(order)
        await self._base_repo.delete_po(po)

    async def find_all(self):
        pos = await self._base_repo.query_po_by_spec(None)
        return [self._mapper.map_reverse(po) for po in pos]

    # ... 还需要实现 10+ 个方法
    """
    )

    print("\n【V4 - RepositoryAdapter】(~50 行核心业务逻辑)")
    print("=" * 60)
    print(
        """
class OrderRepositoryExample(RepositoryAdapter[Order, OrderModel, ID]):
    def __init__(self, session, actor):
        mapper = OrderMapperV3()
        base_repo = BaseRepository(...)
        super().__init__(repository=base_repo, mapper=mapper)

    # ✅ 自动继承 12+ CRUD 方法：
    # - get(id)
    # - save(order)
    # - delete(order)
    # - list(spec)
    # - find_one(spec)
    # - find_all(spec)
    # - find_page(spec, page)
    # - count(spec)
    # - exists(spec)
    # - save_all(orders)
    # - delete_all(orders)

    # 只需定义特殊查询
    async def find_unpaid(self):
        spec = FluentBuilder(...).equals("status", "pending").build()
        return await self.list(spec)  # 使用继承的方法

    async def find_by_customer(self, customer_id):
        spec = FluentBuilder(...).equals("customer_id", ...).build()
        return await self.list(spec)  # 使用继承的方法
    """
    )

    print("\n✨ 优势对比：")
    print("=" * 60)
    print("✅ 代码量减少：67% (150行 → 50行)")
    print("✅ 自动继承：12+ CRUD 方法")
    print("✅ 类型安全：泛型 + 静态检查")
    print("✅ 开发体验：类似 Legend 的简洁性")
    print("✅ 架构优势：保持 Bento 的 Hexagonal Architecture")
    print("✅ 灵活性：可覆盖任何继承的方法")


async def main():
    """Main demo"""
    print("\n" + "=" * 60)
    print("RepositoryAdapter 完整演示（Legend 风格）")
    print("=" * 60)
    print("\n这个演示展示如何使用现有的 RepositoryAdapter：")
    print("  1. 基础 CRUD 操作（自动继承）")
    print("  2. 自定义查询（只定义特殊查询）")
    print("  3. Specification 查询（继承的方法）")
    print("  4. 代码对比（V3 vs V4）")

    await demo_basic_crud()
    await demo_custom_queries()
    await demo_specification_queries()
    await demo_comparison()

    print("\n" + "=" * 60)
    print("演示完成！")
    print("=" * 60)
    print("\n📚 更多信息:")
    print(
        "  - RepositoryAdapter 源码: src/bento/infrastructure/repository/adapter.py"
    )
    print(
        "  - OrderRepository 示例: "
        "applications/ecommerce/modules/order/persistence/repositories/order_repository.py"
    )
    print("  - FluentBuilder 文档: docs/guides/FLUENT_SPECIFICATION_GUIDE.md")
    print("\n💡 关键要点:")
    print("  - RepositoryAdapter 已经存在，无需创建新的基类")
    print("  - 继承 RepositoryAdapter 即可自动获得所有 CRUD 方法")
    print("  - 只需定义业务特定的查询方法")
    print("  - 代码量减少 67%，类似 Legend 的开发体验！")
    print()


if __name__ == "__main__":
    asyncio.run(main())
