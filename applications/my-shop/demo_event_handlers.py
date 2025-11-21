#!/usr/bin/env python3
"""
演示 InProcessMessageBus 和事件处理器的实际工作流程

这个脚本展示：
1. 创建订单并触发事件
2. 多个 Handler 接收并处理事件
3. 完整的事件驱动流程

Run: uv run python applications/my-shop/demo_event_handlers.py
"""

import asyncio
import sys
from pathlib import Path

# Bento framework imports
from bento.core.ids import ID
from bento.infrastructure.database import DatabaseConfig, create_async_engine_from_config
from bento.infrastructure.projection.projector import OutboxProjector
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# Add application to path
sys.path.insert(0, str(Path(__file__).parent))

from bento.adapters.messaging.inprocess import InProcessMessageBus
from bento.persistence.sqlalchemy.outbox_sql import SqlAlchemyOutbox
from bento.persistence.uow import SQLAlchemyUnitOfWork

from contexts.catalog.domain.product import Product
from contexts.catalog.infrastructure.repositories.product_repository_impl import (
    ProductRepository,
)
from contexts.ordering.application.commands.create_order import (
    CreateOrderCommand,
    CreateOrderUseCase,
    OrderItemInput,
)
from contexts.ordering.domain.events.ordercreated_event import OrderCreatedEvent
from contexts.ordering.domain.order import Order
from contexts.ordering.infrastructure.repositories.order_repository_impl import (
    OrderRepository,
)

# =============================================================================
# Event Handlers
# =============================================================================


class InventoryHandler:
    """库存管理 Handler"""

    async def handle_order_created(self, event: OrderCreatedEvent):
        print("\n📦 [Inventory] 处理订单创建事件")
        print(f"   订单 ID: {event.order_id}")

        for item in event.items:
            product_id = item["product_id"]
            quantity = item["quantity"]
            print(f"   ✅ 库存已扣减: Product {product_id} (-{quantity} 件)")


class NotificationHandler:
    """通知 Handler"""

    async def handle_order_created(self, event: OrderCreatedEvent):
        print("\n📧 [Notification] 发送订单确认邮件")
        print(f"   收件人: Customer {event.customer_id}")
        print(f"   主题: 订单创建成功 #{event.order_id}")
        print(f"   内容: 您的订单金额为 ${event.total:.2f}，包含 {event.item_count} 件商品")


class AnalyticsHandler:
    """数据分析 Handler"""

    async def handle_order_created(self, event: OrderCreatedEvent):
        print("\n📊 [Analytics] 记录订单指标")
        print("   事件类型: order_created")
        print(f"   订单金额: ${event.total:.2f}")
        print(f"   商品数量: {event.item_count}")
        print(f"   发生时间: {event.occurred_at}")


class OrderReadModelProjector:
    """订单读模型投影器"""

    async def handle_order_created(self, event: OrderCreatedEvent):
        print("\n📖 [ReadModel] 创建订单读模型")
        print(f"   订单 ID: {event.order_id}")
        print("   状态: pending")
        print("   可搜索字段已建立索引")


# =============================================================================
# Helper Functions
# =============================================================================


def register_repositories(uow: SQLAlchemyUnitOfWork) -> None:
    """注册仓储"""
    uow.register_repository(Product, lambda s: ProductRepository(s))
    uow.register_repository(Order, lambda s: OrderRepository(s))


async def setup_message_bus_with_handlers():
    """设置 MessageBus 并注册所有 Handler"""
    print("\n🔧 设置 InProcessMessageBus...")
    bus = InProcessMessageBus(source="demo")

    # 启动 MessageBus
    await bus.start()
    print("✅ MessageBus 已启动")

    # 创建 Handler 实例
    inventory_handler = InventoryHandler()
    notification_handler = NotificationHandler()
    analytics_handler = AnalyticsHandler()
    read_model_projector = OrderReadModelProjector()

    # 订阅 OrderCreatedEvent
    await bus.subscribe(OrderCreatedEvent, inventory_handler.handle_order_created)
    await bus.subscribe(OrderCreatedEvent, notification_handler.handle_order_created)
    await bus.subscribe(OrderCreatedEvent, analytics_handler.handle_order_created)
    await bus.subscribe(OrderCreatedEvent, read_model_projector.handle_order_created)

    print("✅ 已注册 4 个事件处理器：")
    print("   1. InventoryHandler - 库存管理")
    print("   2. NotificationHandler - 通知发送")
    print("   3. AnalyticsHandler - 数据分析")
    print("   4. OrderReadModelProjector - 读模型同步")

    return bus


# =============================================================================
# Main Demo
# =============================================================================


async def main():
    """演示完整的事件驱动流程"""
    print("=" * 70)
    print("🎬 InProcessMessageBus 事件处理器演示")
    print("=" * 70)

    # Setup database
    script_dir = Path(__file__).parent
    db_path = script_dir / "my_shop.db"
    db_config = DatabaseConfig(
        url=f"sqlite+aiosqlite:///{db_path.absolute()}",
        echo=False,
    )

    engine = create_async_engine_from_config(db_config)
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    # Step 1: 设置 MessageBus 和 Handler
    bus = await setup_message_bus_with_handlers()

    # Step 2: 创建测试产品
    print("\n" + "=" * 70)
    print("1️⃣ 创建测试产品")
    print("=" * 70)

    product_id = ID.generate()
    product = Product(
        id=product_id,
        name="演示商品",
        description="用于展示事件处理的商品",
        price=299.0,
    )

    async with session_factory() as session:
        outbox = SqlAlchemyOutbox(session)
        uow = SQLAlchemyUnitOfWork(session, outbox)
        register_repositories(uow)
        async with uow:
            product_repo = uow.repository(Product)
            await product_repo.save(product)
            await uow.commit()

    print(f"✅ 产品创建成功: {product.name} (${product.price})")

    # Step 3: 创建订单
    print("\n" + "=" * 70)
    print("2️⃣ 创建订单（触发事件）")
    print("=" * 70)

    customer_id = "demo-customer-" + str(ID.generate())[:8]

    async with session_factory() as session:
        outbox = SqlAlchemyOutbox(session)
        uow = SQLAlchemyUnitOfWork(session, outbox)
        register_repositories(uow)
        use_case = CreateOrderUseCase(uow)

        command = CreateOrderCommand(
            customer_id=customer_id,
            items=[
                OrderItemInput(
                    product_id=product_id,
                    product_name="演示商品",
                    quantity=2,
                    unit_price=299.0,
                )
            ],
        )

        async with uow:
            order = await use_case.handle(command)
            await uow.commit()

        order_id = order.id

    print("✅ 订单创建成功:")
    print(f"   订单 ID: {order_id}")
    print(f"   客户 ID: {customer_id}")
    print("   总金额: $598.00 (2 件 × $299.00)")

    # Step 4: 启动 OutboxProjector 处理事件
    print("\n" + "=" * 70)
    print("3️⃣ OutboxProjector 处理 Outbox 事件")
    print("=" * 70)

    projector = OutboxProjector(
        session_factory=session_factory,
        message_bus=bus,
        tenant_id="default",
        batch_size=10,
    )

    print("🔄 处理所有待发布的事件...")
    published_count = await projector.publish_all()
    print(f"✅ 已发布 {published_count} 个事件")

    # 等待异步 Handler 执行
    await asyncio.sleep(0.5)

    # Step 5: 总结
    print("\n" + "=" * 70)
    print("4️⃣ 演示总结")
    print("=" * 70)

    print("\n✅ 完整的事件流程：")
    print("   1. 用户创建订单 (HTTP Request)")
    print("   2. Order 聚合根生成 OrderCreatedEvent")
    print("   3. 事件持久化到 Outbox 表 (status=NEW)")
    print("   4. OutboxProjector 读取 NEW 事件")
    print("   5. 发布到 InProcessMessageBus")
    print("   6. 4 个 Handler 并行处理：")
    print("      → 库存自动扣减 ✓")
    print("      → 邮件通知发送 ✓")
    print("      → 数据指标记录 ✓")
    print("      → 读模型同步 ✓")
    print("   7. 事件状态更新为 SENT")

    print("\n🎯 这就是 InProcessMessageBus 的实际用途：")
    print("   • 解耦业务模块")
    print("   • 异步处理副作用")
    print("   • 提升系统可扩展性")
    print("   • 保证事件可靠传递")

    return 0


if __name__ == "__main__":
    print()
    exit_code = asyncio.run(main())
    print("\n" + "=" * 70)
    print("✅ 演示完成！")
    print("=" * 70)
    sys.exit(exit_code)
