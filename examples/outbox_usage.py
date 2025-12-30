"""Outbox 智能路由使用示例"""

from datetime import datetime, UTC
from uuid import uuid4

from bento.persistence.outbox.record import OutboxRecord
from bento.persistence.outbox.routing import (
    RoutingConfigBuilder,
    create_simple_routing,
    create_conditional_routing,
    create_sampling_routing,
)


def example_simple_routing():
    """简单路由示例"""
    print("🔄 简单路由示例")

    # 创建简单的 DomainEvent 模拟
    class ProductCreatedEvent:
        def __init__(self):
            self.event_id = uuid4()
            self.topic = "product.created"
            self.occurred_at = datetime.now(UTC)
            self.tenant_id = "shop-001"
            self.aggregate_id = "prod-123"
            self.schema_version = 1

        def to_payload(self):
            return {
                "product_id": "prod-123",
                "name": "iPhone 15",
                "price": 999.00,
                "category": "electronics"
            }

    # 创建事件
    event = ProductCreatedEvent()

    # 简单路由：直接指定目标
    record = OutboxRecord.from_domain_event(event)
    record.routing_key = "catalog.product.created"

    print(f"📦 Event ID: {record.id}")
    print(f"🎯 Routing Key: {record.routing_key}")
    print(f"📄 Payload: {record.payload}")
    print()


def example_conditional_routing():
    """条件路由示例"""
    print("🔀 条件路由示例")

    class ProductUpdatedEvent:
        def __init__(self, price: float, category: str):
            self.event_id = uuid4()
            self.topic = "product.updated"
            self.occurred_at = datetime.now(UTC)
            self.tenant_id = "shop-001"
            self.aggregate_id = "prod-456"
            self.schema_version = 1
            self._price = price
            self._category = category

        def to_payload(self):
            return {
                "product_id": "prod-456",
                "price": self._price,
                "category": self._category,
                "visible": True
            }

    # 创建高价商品更新事件
    event = ProductUpdatedEvent(price=1500.00, category="electronics")

    # 配置条件路由
    routing_config = (
        RoutingConfigBuilder()
        .add_target(
            destination="search.index",
            conditions={"payload.visible": True}  # 只有可见的商品才建索引
        )
        .add_target(
            destination="vip.notifications",
            conditions={"payload.price": {"$gt": 1000}},  # 高价商品通知 VIP
            transform={"include_fields": ["product_id", "price"]}  # 只发送必要字段
        )
        .add_target(
            destination="fraud.detection",
            conditions={
                "payload.category": "electronics",
                "payload.price": {"$gt": 500}
            },
            delay_seconds=30  # 延迟 30 秒检测
        )
        .set_fallback("default.events")
        .build()
    )

    # 创建记录
    record = OutboxRecord.from_domain_event(event, routing_config)

    print(f"📦 Event ID: {record.id}")
    print(f"🔧 Routing Config: {record.routing_config}")
    print(f"📄 Payload: {record.payload}")
    print()


def example_sampling_routing():
    """采样路由示例"""
    print("🎲 采样路由示例")

    class UserActivityEvent:
        def __init__(self, action: str):
            self.event_id = uuid4()
            self.topic = "user.activity"
            self.occurred_at = datetime.now(UTC)
            self.tenant_id = "app-001"
            self.aggregate_id = "user-789"
            self.schema_version = 1
            self._action = action

        def to_payload(self):
            return {
                "user_id": "user-789",
                "action": self._action,
                "timestamp": self.occurred_at.isoformat(),
                "trackable": True
            }

    # 创建用户活动事件
    event = UserActivityEvent("page_view")

    # 配置采样路由
    routing_config = (
        RoutingConfigBuilder()
        .add_target(
            destination="analytics.events",
            conditions={"payload.trackable": True},
            sampling_rate=0.1  # 10% 采样
        )
        .add_target(
            destination="realtime.dashboard",
            conditions={"payload.action": "page_view"},
            sampling_rate=0.01  # 1% 采样，用于实时监控
        )
        .build()
    )

    record = OutboxRecord.from_domain_event(event, routing_config)

    print(f"📦 Event ID: {record.id}")
    print(f"🔧 Routing Config: {record.routing_config}")
    print(f"📄 Payload: {record.payload}")
    print()


def example_complex_routing():
    """复杂路由示例"""
    print("🚀 复杂路由示例")

    class OrderCreatedEvent:
        def __init__(self, total: float, customer_tier: str):
            self.event_id = uuid4()
            self.topic = "order.created"
            self.occurred_at = datetime.now(UTC)
            self.tenant_id = "shop-premium"
            self.aggregate_id = f"order-{uuid4().hex[:8]}"
            self.schema_version = 1
            self._total = total
            self._customer_tier = customer_tier

        def to_payload(self):
            return {
                "order_id": self.aggregate_id,
                "total": self._total,
                "customer_tier": self._customer_tier,
                "items_count": 3,
                "priority": "high" if self._total > 500 else "normal"
            }

    # 创建大订单事件
    event = OrderCreatedEvent(total=800.00, customer_tier="vip")

    # 复杂路由配置
    routing_config = (
        RoutingConfigBuilder()
        # 所有订单都要记录
        .add_target(
            destination="orders.audit",
            transform={"exclude_fields": ["customer_tier"]}  # 审计不需要客户等级
        )
        # 高价值订单特殊处理
        .add_target(
            destination="fulfillment.priority",
            conditions={
                "payload.total": {"$gte": 500},
                "payload.customer_tier": {"$in": ["vip", "premium"]}
            },
            delay_seconds=0,  # 立即处理
            retry_policy="aggressive"
        )
        # 库存更新（延迟处理避免并发）
        .add_target(
            destination="inventory.reserve",
            delay_seconds=10,
            transform={"include_fields": ["order_id", "items_count"]}
        )
        # 营销分析（采样）
        .add_target(
            destination="marketing.analysis",
            conditions={"payload.customer_tier": {"$ne": "guest"}},
            sampling_rate=0.2,
            transform={
                "add_fields": {"analysis_type": "order_behavior"},
                "field_mapping": {"total": "order_value"}
            }
        )
        .set_fallback("orders.deadletter")
        .set_strategy("all_or_nothing")  # 要么全部成功，要么全部失败
        .build()
    )

    record = OutboxRecord.from_domain_event(event, routing_config)

    print(f"📦 Event ID: {record.id}")
    print(f"🏷️  Topic: {record.topic}")
    print(f"🆔 Aggregate: {record.aggregate_type}#{record.aggregate_id}")
    print(f"🕐 Occurred: {record.occurred_at}")
    print(f"🔧 Routing Config: {record.routing_config}")
    print(f"📊 Metadata: {record.metadata}")
    print()


def example_convenience_functions():
    """便捷函数示例"""
    print("⚡ 便捷函数示例")

    # 简单路由
    simple_config = create_simple_routing("catalog.product.sync")
    print(f"Simple: {simple_config}")

    # 条件路由
    conditional_config = create_conditional_routing([
        ("high_value.orders", {"payload.total": {"$gt": 1000}}),
        ("bulk.orders", {"payload.items_count": {"$gte": 10}}),
    ])
    print(f"Conditional: {conditional_config}")

    # 采样路由
    sampling_config = create_sampling_routing("analytics.sample", 0.05)
    print(f"Sampling: {sampling_config}")


if __name__ == "__main__":
    print("🎯 Bento Outbox 智能路由示例\n")

    example_simple_routing()
    example_conditional_routing()
    example_sampling_routing()
    example_complex_routing()
    example_convenience_functions()

    print("✅ 所有示例完成！")
