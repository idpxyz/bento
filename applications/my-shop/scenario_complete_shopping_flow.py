#!/usr/bin/env python3
"""
完整的电商购物场景演示

业务场景：用户 Alice 的购物之旅
1. 浏览商品目录
2. 选择商品加入购物车
3. 创建订单
4. 支付订单
5. 订单发货
6. 订单送达

展示的架构特性：
- Catalog 和 Ordering 两个 Bounded Context
- 事件驱动架构
- InProcessMessageBus 实现模块间通讯
- Outbox Pattern 保证事件可靠传递
- 多个 Handler 协同工作（库存、通知、积分、分析）

Run: uv run python applications/my-shop/scenario_complete_shopping_flow.py
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

from bento.adapters.messaging.inprocess import InProcessMessageBus

# Bento framework imports
from bento.core.ids import ID
from bento.infrastructure.database import DatabaseConfig, create_async_engine_from_config
from bento.infrastructure.projection.projector import OutboxProjector
from bento.persistence.sqlalchemy.outbox_sql import SqlAlchemyOutbox
from bento.persistence.uow import SQLAlchemyUnitOfWork
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

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
from contexts.ordering.domain.events.orderdelivered_event import OrderDeliveredEvent
from contexts.ordering.domain.events.orderpaid_event import OrderPaidEvent
from contexts.ordering.domain.events.ordershipped_event import OrderShippedEvent
from contexts.ordering.domain.order import Order
from contexts.ordering.infrastructure.adapters.services.product_catalog_adapter import (
    ProductCatalogAdapter,
)
from contexts.ordering.infrastructure.repositories.order_repository_impl import (
    OrderRepository,
)

# Add application to path
sys.path.insert(0, str(Path(__file__).parent))
# =============================================================================
# Event Handlers - 模拟真实业务场景
# =============================================================================


class InventoryHandler:
    """库存管理服务"""

    def __init__(self):
        self.inventory = {}  # 简单的内存库存

    async def handle_order_created(self, event: OrderCreatedEvent):
        """订单创建后扣减库存"""
        print("\n📦 [库存系统] 处理订单创建事件")
        print(f"   订单号: {event.order_id}")

        for item in event.items:
            product_id = item["product_id"]
            quantity = item["quantity"]
            product_name = item["product_name"]

            # 扣减库存
            current = self.inventory.get(product_id, 1000)
            new_stock = current - quantity
            self.inventory[product_id] = new_stock

            print(f"   ✅ {product_name}: 库存 {current} → {new_stock}")

        print("   💾 库存更新已保存")


class NotificationHandler:
    """通知服务"""

    async def handle_order_created(self, event: OrderCreatedEvent):
        """订单创建通知"""
        print("\n📧 [通知系统] 发送订单确认邮件")
        print(f"   收件人: {event.customer_id}@example.com")
        print("   主题: 【My Shop】订单创建成功")
        print("   内容:")
        print("   尊敬的客户，您的订单已创建成功！")
        print(f"   订单号: {event.order_id}")
        print(f"   订单金额: ${event.total:.2f}")
        print(f"   商品数量: {event.item_count} 件")
        print("   ✅ 邮件已发送")

    async def handle_order_paid(self, event: OrderPaidEvent):
        """支付成功通知"""
        # 处理 customer_id（可能是字符串或字典）
        customer_id = event.customer_id
        if isinstance(customer_id, dict):
            customer_id = customer_id.get("value", customer_id)

        print("\n💰 [通知系统] 发送支付确认邮件")
        print(f"   收件人: {customer_id}@example.com")
        print("   主题: 【My Shop】支付成功，订单处理中")
        print("   内容:")
        print(f"   您的订单 {event.order_id} 已支付成功！")
        print(f"   支付金额: ${event.total:.2f}")
        print(f"   支付时间: {event.paid_at}")
        print("   我们将尽快为您发货。")
        print("   ✅ 邮件已发送")

    async def handle_order_shipped(self, event: OrderShippedEvent):
        """发货通知"""
        print("\n📦 [通知系统] 发送发货通知邮件")
        print("   收件人: customer@example.com")
        print("   主题: 【My Shop】您的订单已发货")
        print("   内容:")
        print(f"   您的订单 {event.order_id} 已发货！")
        print(f"   物流单号: {event.tracking_number or 'SF1234567890'}")
        print(f"   发货时间: {event.shipped_at}")
        print("   预计 2-3 个工作日送达。")
        print("   ✅ 邮件已发送")

    async def handle_order_delivered(self, event: OrderDeliveredEvent):
        """送达通知"""
        print("\n🎉 [通知系统] 发送送达确认邮件")
        print("   收件人: customer@example.com")
        print("   主题: 【My Shop】订单已送达，请确认签收")
        print("   内容:")
        print(f"   您的订单 {event.order_id} 已送达！")
        print(f"   签收时间: {event.delivered_at}")
        print("   感谢您的购买，期待您的好评！")
        print("   ✅ 邮件已发送")


class LoyaltyProgramHandler:
    """会员积分系统"""

    def __init__(self):
        self.points = {}  # 简单的内存积分系统

    async def handle_order_paid(self, event: OrderPaidEvent):
        """支付成功后赠送积分"""
        points = int(event.total * 0.1)  # 10% 返积分

        # 处理 customer_id（可能是字符串或字典）
        customer_id = event.customer_id
        if isinstance(customer_id, dict):
            customer_id = customer_id.get("value", customer_id)

        current_points = self.points.get(customer_id, 0)
        new_points = current_points + points
        self.points[customer_id] = new_points

        print("\n🎁 [积分系统] 赠送会员积分")
        print(f"   客户: {customer_id}")
        print(f"   本次订单: ${event.total:.2f}")
        print(f"   赠送积分: +{points} 分")
        print(f"   当前总积分: {new_points} 分")
        print("   💾 积分已入账")


class AnalyticsHandler:
    """数据分析系统"""

    def __init__(self):
        self.metrics = {
            "total_orders": 0,
            "total_revenue": 0.0,
            "total_items_sold": 0,
        }

    async def handle_order_created(self, event: OrderCreatedEvent):
        """记录订单创建指标"""
        self.metrics["total_orders"] += 1

        print("\n📊 [分析系统] 记录业务指标")
        print("   事件: order_created")
        print(f"   订单ID: {event.order_id}")
        print(f"   商品数: {event.item_count}")
        print(f"   📈 今日订单数: {self.metrics['total_orders']}")

    async def handle_order_paid(self, event: OrderPaidEvent):
        """记录支付指标"""
        self.metrics["total_revenue"] += event.total

        print("\n📊 [分析系统] 记录支付指标")
        print("   事件: order_paid")
        print(f"   订单ID: {event.order_id}")
        print(f"   金额: ${event.total:.2f}")
        print(f"   💵 今日营收: ${self.metrics['total_revenue']:.2f}")


class OrderReadModelProjector:
    """订单读模型投影器 - CQRS"""

    async def handle_order_created(self, event: OrderCreatedEvent):
        """创建订单读模型"""
        print("\n📖 [读模型系统] 创建订单查询视图")
        print(f"   订单ID: {event.order_id}")
        print("   状态: PENDING")
        print(f"   客户: {event.customer_id}")
        print(f"   金额: ${event.total:.2f}")
        print("   ✅ 读模型已创建，可供查询")

    async def handle_order_paid(self, event: OrderPaidEvent):
        """更新订单状态"""
        print("\n📖 [读模型系统] 更新订单状态")
        print(f"   订单ID: {event.order_id}")
        print("   状态: PENDING → PAID")
        print(f"   支付时间: {event.paid_at}")
        print("   ✅ 读模型已更新")

    async def handle_order_shipped(self, event: OrderShippedEvent):
        """更新订单为已发货状态"""
        print("\n📖 [读模型系统] 更新订单状态")
        print(f"   订单ID: {event.order_id}")
        print("   状态: PAID → SHIPPED")
        print(f"   发货时间: {event.shipped_at}")
        print(f"   物流单号: {event.tracking_number or 'N/A'}")
        print("   ✅ 读模型已更新")

    async def handle_order_delivered(self, event: OrderDeliveredEvent):
        """更新订单为已送达状态"""
        print("\n📖 [读模型系统] 更新订单状态")
        print(f"   订单ID: {event.order_id}")
        print("   状态: SHIPPED → DELIVERED")
        print(f"   送达时间: {event.delivered_at}")
        print("   ✅ 读模型已更新")


# =============================================================================
# 场景主流程
# =============================================================================


def register_repositories(uow: SQLAlchemyUnitOfWork) -> None:
    """注册仓储"""
    uow.register_repository(Product, lambda s: ProductRepository(s))
    uow.register_repository(Order, lambda s: OrderRepository(s))


async def setup_event_handlers(bus: InProcessMessageBus):
    """设置所有事件处理器"""
    # 创建 Handler 实例
    inventory_handler = InventoryHandler()
    notification_handler = NotificationHandler()
    loyalty_handler = LoyaltyProgramHandler()
    analytics_handler = AnalyticsHandler()
    read_model_projector = OrderReadModelProjector()

    # 订阅 OrderCreatedEvent
    await bus.subscribe(OrderCreatedEvent, inventory_handler.handle_order_created)
    await bus.subscribe(OrderCreatedEvent, notification_handler.handle_order_created)
    await bus.subscribe(OrderCreatedEvent, analytics_handler.handle_order_created)
    await bus.subscribe(OrderCreatedEvent, read_model_projector.handle_order_created)

    # 订阅 OrderPaidEvent
    await bus.subscribe(OrderPaidEvent, notification_handler.handle_order_paid)
    await bus.subscribe(OrderPaidEvent, loyalty_handler.handle_order_paid)
    await bus.subscribe(OrderPaidEvent, analytics_handler.handle_order_paid)
    await bus.subscribe(OrderPaidEvent, read_model_projector.handle_order_paid)

    # 订阅 OrderShippedEvent
    await bus.subscribe(OrderShippedEvent, notification_handler.handle_order_shipped)
    await bus.subscribe(OrderShippedEvent, read_model_projector.handle_order_shipped)

    # 订阅 OrderDeliveredEvent
    await bus.subscribe(OrderDeliveredEvent, notification_handler.handle_order_delivered)
    await bus.subscribe(OrderDeliveredEvent, read_model_projector.handle_order_delivered)

    return {
        "inventory": inventory_handler,
        "notification": notification_handler,
        "loyalty": loyalty_handler,
        "analytics": analytics_handler,
    }


async def process_events(session_factory, bus):
    """处理 Outbox 中的事件"""
    projector = OutboxProjector(
        session_factory=session_factory,
        message_bus=bus,
        tenant_id="default",
        batch_size=10,
    )
    await projector.publish_all()
    await asyncio.sleep(0.5)  # 等待异步 Handler 执行


async def main():
    """完整的购物场景"""
    print("=" * 80)
    print("🛒 My Shop - 完整购物场景演示")
    print("=" * 80)
    print("\n场景: 用户 Alice 的购物之旅")
    print("时间: 2025年11月19日")
    print()

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

    # Setup MessageBus and Handlers
    bus = InProcessMessageBus(source="my-shop-scenario")
    await bus.start()
    handlers = await setup_event_handlers(bus)

    print("✅ 系统启动完成")
    print("   - MessageBus: InProcessMessageBus")
    print("   - Event Handlers: 库存、通知、积分、分析、读模型")
    print()

    # =========================================================================
    # 第一步：准备商品目录
    # =========================================================================
    print("\n" + "=" * 80)
    print("📚 第一步：商品上架")
    print("=" * 80)

    products = [
        {
            "id": str(ID.generate()),
            "name": "iPhone 15 Pro",
            "description": "6.1 英寸超视网膜 XDR 显示屏",
            "price": 999.0,
        },
        {
            "id": str(ID.generate()),
            "name": "AirPods Pro 2",
            "description": "主动降噪无线耳机",
            "price": 249.0,
        },
        {
            "id": str(ID.generate()),
            "name": "MacBook Air M3",
            "description": "13 英寸超轻薄笔记本",
            "price": 1299.0,
        },
    ]

    async with session_factory() as session:
        outbox = SqlAlchemyOutbox(session)
        uow = SQLAlchemyUnitOfWork(session, outbox)
        register_repositories(uow)
        async with uow:
            product_repo = uow.repository(Product)
            for p_data in products:
                product = Product(**p_data)
                await product_repo.save(product)
                # 初始化库存
                handlers["inventory"].inventory[p_data["id"]] = 100
            await uow.commit()

    print("\n商品目录:")
    for idx, p in enumerate(products, 1):
        print(f"   {idx}. {p['name']} - ${p['price']:.2f}")
        print(f"      {p['description']}")
        print(f"      库存: {handlers['inventory'].inventory[p['id']]} 件")

    # =========================================================================
    # 第二步：用户浏览并创建订单
    # =========================================================================
    print("\n" + "=" * 80)
    print("👤 第二步：用户 Alice 开始购物")
    print("=" * 80)

    customer_id = "alice"
    print("\n用户 Alice 登录系统...")
    print("浏览商品目录...")
    print("选择了以下商品:")
    print("   - iPhone 15 Pro × 1")
    print("   - AirPods Pro 2 × 2")

    await asyncio.sleep(1)

    print("\n点击【创建订单】按钮...")

    # 创建订单
    async with session_factory() as session:
        outbox = SqlAlchemyOutbox(session)
        uow = SQLAlchemyUnitOfWork(session, outbox)
        register_repositories(uow)
        use_case = CreateOrderUseCase(uow, product_catalog=ProductCatalogAdapter(session))

        command = CreateOrderCommand(
            customer_id=customer_id,
            items=[
                OrderItemInput(
                    product_id=products[0]["id"],
                    product_name=products[0]["name"],
                    quantity=1,
                    unit_price=products[0]["price"],
                ),
                OrderItemInput(
                    product_id=products[1]["id"],
                    product_name=products[1]["name"],
                    quantity=2,
                    unit_price=products[1]["price"],
                ),
            ],
        )

        async with uow:
            order = await use_case.handle(command)
            await uow.commit()

        order_id = order.id
        order_total = order.total

    print("\n✅ 订单创建成功!")
    print(f"   订单号: {order_id}")
    print(f"   订单金额: ${order_total:.2f}")

    # 处理 OrderCreatedEvent
    print("\n" + "-" * 80)
    print("🔄 系统处理 OrderCreatedEvent...")
    print("-" * 80)
    await process_events(session_factory, bus)

    # =========================================================================
    # 第三步：用户支付订单
    # =========================================================================
    await asyncio.sleep(2)

    print("\n" + "=" * 80)
    print("💳 第三步：用户 Alice 支付订单")
    print("=" * 80)

    print("\nAlice 选择支付方式: 微信支付")
    print("输入支付密码...")
    print("支付处理中...")

    await asyncio.sleep(1)

    # 确认支付
    async with session_factory() as session:
        outbox = SqlAlchemyOutbox(session)
        uow = SQLAlchemyUnitOfWork(session, outbox)
        register_repositories(uow)
        async with uow:
            order_repo = uow.repository(Order)
            order = await order_repo.get(order_id)
            order.confirm_payment()
            await order_repo.save(order)
            await uow.commit()

    print("\n✅ 支付成功!")
    print(f"   订单号: {order_id}")
    print(f"   支付金额: ${order_total:.2f}")
    print(f"   支付时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 处理 OrderPaidEvent
    print("\n" + "-" * 80)
    print("🔄 系统处理 OrderPaidEvent...")
    print("-" * 80)
    await process_events(session_factory, bus)

    # =========================================================================
    # 第四步：订单发货
    # =========================================================================
    await asyncio.sleep(2)

    print("\n" + "=" * 80)
    print("📦 第四步：仓库处理发货")
    print("=" * 80)

    print("\n仓库系统接收订单...")
    print("商品拣货中...")
    print("打包完成...")
    print("交付快递公司...")

    await asyncio.sleep(1)

    # 订单发货
    async with session_factory() as session:
        outbox = SqlAlchemyOutbox(session)
        uow = SQLAlchemyUnitOfWork(session, outbox)
        register_repositories(uow)
        async with uow:
            order_repo = uow.repository(Order)
            order = await order_repo.get(order_id)
            order.ship()
            await order_repo.save(order)
            await uow.commit()

    print("\n✅ 订单已发货!")
    print(f"   订单号: {order_id}")
    print("   物流单号: SF1234567890")
    print("   预计送达: 2-3 个工作日")

    # 处理 OrderShippedEvent
    print("\n" + "-" * 80)
    print("🔄 系统处理 OrderShippedEvent...")
    print("-" * 80)
    await process_events(session_factory, bus)

    # =========================================================================
    # 第五步：订单送达
    # =========================================================================
    await asyncio.sleep(2)

    print("\n" + "=" * 80)
    print("🚚 第五步：订单送达")
    print("=" * 80)

    print("\n快递配送中...")
    print("快递员联系客户...")
    print("客户签收...")

    await asyncio.sleep(1)

    # 订单完成
    async with session_factory() as session:
        outbox = SqlAlchemyOutbox(session)
        uow = SQLAlchemyUnitOfWork(session, outbox)
        register_repositories(uow)
        async with uow:
            order_repo = uow.repository(Order)
            order = await order_repo.get(order_id)
            order.deliver()
            await order_repo.save(order)
            await uow.commit()

    print("\n✅ 订单已送达!")
    print(f"   订单号: {order_id}")
    print(f"   签收时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("   订单状态: 已完成")

    # 处理 OrderDeliveredEvent
    print("\n" + "-" * 80)
    print("🔄 系统处理 OrderDeliveredEvent...")
    print("-" * 80)
    await process_events(session_factory, bus)

    # =========================================================================
    # 总结
    # =========================================================================
    print("\n" + "=" * 80)
    print("📊 购物场景总结")
    print("=" * 80)

    print("\n✅ Alice 的购物之旅圆满完成!")
    print("\n订单信息:")
    print(f"   订单号: {order_id}")
    print(f"   客户: {customer_id}")
    print("   商品: iPhone 15 Pro × 1, AirPods Pro 2 × 2")
    print(f"   金额: ${order_total:.2f}")
    print("   状态: 已完成")

    print("\n系统指标:")
    print(f"   总订单数: {handlers['analytics'].metrics['total_orders']}")
    print(f"   总营收: ${handlers['analytics'].metrics['total_revenue']:.2f}")

    print("\n会员积分:")
    print(f"   Alice 当前积分: {handlers['loyalty'].points.get(customer_id, 0)} 分")

    print("\n库存变化:")
    for p in products[:2]:  # 只显示购买的商品
        print(f"   {p['name']}: {handlers['inventory'].inventory[p['id']]} 件")

    print("\n" + "=" * 80)
    print("🎯 本场景展示了以下架构特性:")
    print("=" * 80)
    print("""
✅ DDD 设计
   - Catalog 和 Ordering 两个 Bounded Context
   - Order 作为聚合根管理订单生命周期
   - Product 聚合根管理商品信息

✅ 事件驱动架构
   - OrderCreatedEvent: 订单创建事件
   - OrderPaidEvent: 订单支付事件
   - 事件触发多个业务流程

✅ Outbox Pattern
   - 事件持久化到 Outbox 表
   - 保证事件不丢失
   - OutboxProjector 可靠投递

✅ InProcessMessageBus
   - 进程内高性能事件分发
   - 支持多订阅者
   - 解耦业务模块

✅ 多系统协同
   - 库存系统: 自动扣减库存
   - 通知系统: 发送邮件通知
   - 积分系统: 自动计算和赠送积分
   - 分析系统: 实时记录业务指标
   - 读模型系统: CQRS 查询优化

✅ 可扩展性
   - 新增业务功能只需添加新的 Handler
   - 现有代码无需修改
   - 符合开闭原则
""")

    print("=" * 80)
    print("✅ 场景演示完成!")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    print()
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
