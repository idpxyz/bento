"""
示例：实际的事件处理器实现

展示 InProcessMessageBus 在生产环境中的实际用途
"""

from contexts.ordering.domain.events.ordercreated_event import OrderCreatedEvent
from contexts.ordering.domain.events.orderpaid_event import OrderPaidEvent


class InventoryHandler:
    """库存管理 Handler - 自动扣减库存"""

    async def handle_order_created(self, event: OrderCreatedEvent):
        """订单创建后扣减库存"""
        print(f"📦 [Inventory] 处理订单创建: {event.order_id}")

        for item in event.items:
            product_id = item["product_id"]
            quantity = item["quantity"]

            # TODO: 实现库存扣减逻辑
            # await product_service.reduce_stock(product_id, quantity)

            print(f"   ✅ 库存已扣减: Product {product_id} (-{quantity})")


class NotificationHandler:
    """通知 Handler - 发送邮件/短信"""

    async def handle_order_created(self, event: OrderCreatedEvent):
        """订单创建通知"""
        print("📧 [Notification] 发送订单确认邮件")
        print(f"   To: Customer {event.customer_id}")
        print(f"   Subject: 订单创建成功 #{event.order_id}")

        # TODO: 实现邮件发送
        # await email_service.send_order_confirmation(event)

    async def handle_order_paid(self, event: OrderPaidEvent):
        """支付成功通知"""
        print("💰 [Notification] 发送支付成功通知")
        print(f"   订单 {event.order_id} 已支付 ${event.total}")

        # TODO: 实现支付通知
        # await email_service.send_payment_confirmation(event)


class AnalyticsHandler:
    """数据分析 Handler - 记录业务指标"""

    async def handle_order_created(self, event: OrderCreatedEvent):
        """记录订单创建指标"""
        print("📊 [Analytics] 记录订单指标")
        print(f"   - Order ID: {event.order_id}")
        print(f"   - Total: ${event.total}")
        print(f"   - Items: {event.item_count}")

        # TODO: 发送到数据分析平台
        # await analytics.track("order_created", event.to_dict())

    async def handle_order_paid(self, event: OrderPaidEvent):
        """记录支付指标"""
        print("📊 [Analytics] 记录支付指标")
        print(f"   - Order ID: {event.order_id}")
        print(f"   - Revenue: ${event.total}")

        # TODO: 更新销售仪表板
        # await analytics.track("payment_received", event.to_dict())


class OrderReadModelProjector:
    """订单读模型投影器 - CQRS 读模型同步"""

    async def handle_order_created(self, event: OrderCreatedEvent):
        """创建订单读模型"""
        print(f"📖 [ReadModel] 创建订单读模型: {event.order_id}")

        # TODO: 创建优化的读模型
        # read_model = OrderReadModel(
        #     order_id=event.order_id,
        #     customer_id=event.customer_id,
        #     total=event.total,
        #     status="pending",
        #     searchable_text=self._build_search_text(event)
        # )
        # await read_model_repo.save(read_model)

    async def handle_order_paid(self, event: OrderPaidEvent):
        """更新订单读模型状态"""
        print(f"📖 [ReadModel] 更新订单状态为已支付: {event.order_id}")

        # TODO: 更新读模型
        # await read_model_repo.update_status(event.order_id, "paid")


class LoyaltyProgramHandler:
    """会员积分 Handler - 自动积分奖励"""

    async def handle_order_paid(self, event: OrderPaidEvent):
        """支付成功后赠送积分"""
        points = int(event.total * 0.1)  # 10% 返积分

        print("🎁 [Loyalty] 赠送积分")
        print(f"   Customer: {event.customer_id}")
        print(f"   Points: {points}")

        # TODO: 实现积分赠送
        # await loyalty_service.add_points(
        #     customer_id=event.customer_id,
        #     points=points,
        #     reason=f"订单 {event.order_id} 支付"
        # )


# =============================================================================
# 如何在 bootstrap.py 中注册这些 Handler
# =============================================================================

"""
在你的 bootstrap.py 的 lifespan 函数中：

async def lifespan(app: FastAPI):
    # 创建 MessageBus
    bus = InProcessMessageBus(source="my-shop")

    # 创建 Handler 实例
    inventory_handler = InventoryHandler()
    notification_handler = NotificationHandler()
    analytics_handler = AnalyticsHandler()
    read_model_projector = OrderReadModelProjector()
    loyalty_handler = LoyaltyProgramHandler()

    # 订阅事件
    await bus.subscribe(OrderCreatedEvent, inventory_handler.handle_order_created)
    await bus.subscribe(OrderCreatedEvent, notification_handler.handle_order_created)
    await bus.subscribe(OrderCreatedEvent, analytics_handler.handle_order_created)
    await bus.subscribe(OrderCreatedEvent, read_model_projector.handle_order_created)

    await bus.subscribe(OrderPaidEvent, notification_handler.handle_order_paid)
    await bus.subscribe(OrderPaidEvent, analytics_handler.handle_order_paid)
    await bus.subscribe(OrderPaidEvent, read_model_projector.handle_order_paid)
    await bus.subscribe(OrderPaidEvent, loyalty_handler.handle_order_paid)

    # 启动 OutboxProjector
    projector = OutboxProjector(
        session_factory=session_factory,
        message_bus=bus,
    )

    projector_task = asyncio.create_task(projector.run())

    try:
        yield
    finally:
        projector_task.cancel()
"""
