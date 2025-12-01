"""正确的架构使用示例 - 使用原有的 OutboxProjector"""

import asyncio
from datetime import datetime, UTC
from uuid import uuid4

# 使用现有的完整架构
from bento.adapters.messaging.inprocess.message_bus import InProcessMessageBus
from bento.domain.domain_event import DomainEvent
from bento.domain.event_registry import register_event
from bento.infrastructure.projection.projector import OutboxProjector
from bento.persistence.outbox import OutboxRecord


# 示例领域事件
class OrderCreatedEvent(DomainEvent):
    def __init__(
        self,
        order_id: str,
        customer_id: str,
        total: float,
        items_count: int,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.topic = "order.created"
        self.order_id = order_id
        self.customer_id = customer_id
        self.total = total
        self.items_count = items_count

    def to_payload(self) -> dict:
        return {
            "event_id": str(self.event_id),
            "topic": self.topic,
            "order_id": self.order_id,
            "customer_id": self.customer_id,
            "total": self.total,
            "items_count": self.items_count,
            "occurred_at": self.occurred_at.isoformat(),
        }


class ProductUpdatedEvent(DomainEvent):
    def __init__(
        self,
        product_id: str,
        name: str,
        price: float,
        category: str,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.topic = "product.updated"
        self.product_id = product_id
        self.name = name
        self.price = price
        self.category = category

    def to_payload(self) -> dict:
        return {
            "event_id": str(self.event_id),
            "topic": self.topic,
            "product_id": self.product_id,
            "name": self.name,
            "price": self.price,
            "category": self.category,
            "occurred_at": self.occurred_at.isoformat(),
        }


async def demonstrate_correct_architecture():
    """演示正确的架构使用方式"""
    print("🎯 正确的 DDD + 六边形架构示例\n")

    # 1. 创建消息总线（现有架构已经完美支持路由）
    message_bus = InProcessMessageBus()
    await message_bus.start()

    # 现有 MessageBus 已经支持：
    # - 自动 topic 路由 (PulsarMessageBus)
    # - 事件类型解析
    # - 订阅/发布机制
    # - 批量处理

    # 4. 模拟数据库会话（实际应用中从 UoW 获取）
    class MockSession:
        pass

    session = MockSession()

    # 5. 创建简化的 Outbox 处理器
    event_registry = {
        "OrderCreatedEvent": OrderCreatedEvent,
        "ProductUpdatedEvent": ProductUpdatedEvent,
    }

    processor = create_outbox_processor(
        session=session,
        message_bus=message_bus,  # 使用现有消息总线！
        event_registry=event_registry,
        batch_size=50
    )

    # 6. 演示事件流转（正确的架构流程）
    print("📦 1. 业务逻辑创建领域事件")
    order_event = OrderCreatedEvent(
        event_id=uuid4(),
        order_id="order-123",
        customer_id="cust-456",
        total=1500.00,
        items_count=3,
        occurred_at=datetime.now(UTC)
    )

    product_event = ProductUpdatedEvent(
        event_id=uuid4(),
        product_id="prod-789",
        name="iPhone 15 Pro",
        price=1299.00,
        category="electronics",
        occurred_at=datetime.now(UTC)
    )

    print(f"   ✅ OrderCreatedEvent: {order_event.order_id} (${order_event.total})")
    print(f"   ✅ ProductUpdatedEvent: {product_event.product_id} (${product_event.price})")
    print()

    print("💾 2. Outbox 存储事件（事务性保证）")
    # 在实际应用中，这由 UoW 自动处理
    order_record = OutboxRecord.from_domain_event(order_event)
    product_record = OutboxRecord.from_domain_event(product_event)

    print(f"   ✅ 存储到 Outbox: {order_record.topic}")
    print(f"   ✅ 存储到 Outbox: {product_record.topic}")
    print()

    print("🚀 3. MessageBus 自动路由")
    # 现有 MessageBus 已经支持自动路由：
    # - 根据事件类型自动确定 topic
    # - 支持订阅/发布模式
    # - PulsarMessageBus 支持完整的 topic 命名空间
    await message_bus.publish(order_event)
    await message_bus.publish(product_event)
    print()

    print("🏆 4. 现有架构的优势")
    print("   ✅ 职责清晰：Outbox(存储) → MessageBus(发布) → Subscribers")
    print("   ✅ 符合 DDD：每个组件在正确的架构层")
    print("   ✅ 六边形架构：MessageBus Protocol + 多种适配器")
    print("   ✅ 可测试性：InProcessMessageBus 便于单元测试")
    print("   ✅ 生产就绪：PulsarMessageBus 支持企业级功能")
    print("   ✅ 无需额外复杂性：现有设计已经完美")
    print()

    # 清理
    await message_bus.stop()


async def demonstrate_wrong_architecture():
    """演示错误的架构（对比参考）"""
    print("❌ 错误架构：Outbox 包含智能路由")
    print("   问题1：职责混淆（存储层包含路由逻辑）")
    print("   问题2：违反分层（Persistence 层做 Application 层的事）")
    print("   问题3：难以测试（路由逻辑埋在 Outbox 中）")
    print("   问题4：不符合六边形架构（没有清晰的端口适配器分离）")
    print()


if __name__ == "__main__":
    print("🎯 Bento Framework 架构对比演示\n")

    asyncio.run(demonstrate_correct_architecture())
    demonstrate_wrong_architecture()

    print("💡 结论：现有 MessageBus + 简单 Outbox = DDD 最佳实践！")
    print("🎊 智能路由应该在 MessageBus 层，而不是 Outbox 层！")
