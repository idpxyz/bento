"""Hybrid Messaging Example - Smart event routing based on business context.

This example demonstrates how to use HybridMessageBus for intelligent
event publishing based on business requirements:
- Intra-BC events: Fast synchronous publishing
- Inter-BC events: Reliable asynchronous publishing
- Critical events: Hybrid strategies for best of both worlds
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime

from bento.domain.domain_event import DomainEvent
from bento.application.ports.hybrid_message_bus import (
    PublishConfig, PublishStrategy, EventScope, PublishStrategies
)
from bento.adapters.messaging.hybrid.message_bus import DefaultHybridMessageBus
from bento.adapters.messaging.inprocess.message_bus import InProcessMessageBus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Sample events for different scenarios
@dataclass(frozen=True)
class OrderCreatedEvent(DomainEvent):
    """Critical inter-BC event - needs reliable delivery."""
    order_id: str = ""
    customer_id: str = ""
    total_amount: float = 0.0
    topic: str = "order.created"
    bounded_context: str = "orders"


@dataclass(frozen=True)
class OrderStatusUpdatedEvent(DomainEvent):
    """Intra-BC event - needs fast delivery."""
    order_id: str = ""
    old_status: str = ""
    new_status: str = ""
    topic: str = "order.status_updated"
    bounded_context: str = "orders"


@dataclass(frozen=True)
class InventoryReservedEvent(DomainEvent):
    """Inter-BC event - reliable delivery required."""
    product_id: str = ""
    quantity: int = 0
    reservation_id: str = ""
    topic: str = "inventory.reserved"
    bounded_context: str = "inventory"


@dataclass(frozen=True)
class UINotificationEvent(DomainEvent):
    """Intra-BC event - fast delivery, not critical."""
    user_id: str = ""
    message: str = ""
    topic: str = "ui.notification"
    bounded_context: str = "frontend"


class MockOutbox:
    """Mock Outbox for demonstration."""

    def __init__(self):
        self.events = []

    async def add(self, topic: str, payload: dict) -> None:
        self.events.append({"topic": topic, "payload": payload})
        logger.info(f"📦 Added to Outbox: {topic}")


async def hybrid_messaging_demo():
    """Demonstrate intelligent hybrid messaging."""

    print("🎯 Hybrid Messaging Demo")
    print("=" * 30)

    # 1. Setup HybridMessageBus
    print("\n🔧 Setting up HybridMessageBus...")

    sync_bus = InProcessMessageBus(source="hybrid-demo")
    mock_outbox = MockOutbox()

    hybrid_bus = DefaultHybridMessageBus(
        sync_bus=sync_bus,
        async_outbox=mock_outbox
    )

    # 2. Configure event-specific strategies
    print("\n⚙️ Configuring event publishing strategies...")

    # Critical inter-BC events: Reliable async + sync confirmation
    hybrid_bus.configure_event(
        OrderCreatedEvent,
        PublishStrategies.CRITICAL_HYBRID
    )

    # Inter-BC inventory events: Reliable async only
    hybrid_bus.configure_event(
        InventoryReservedEvent,
        PublishStrategies.INTER_BC_RELIABLE
    )

    # Intra-BC status updates: Fast sync only
    hybrid_bus.configure_event(
        OrderStatusUpdatedEvent,
        PublishStrategies.INTRA_BC_FAST
    )

    # UI notifications: Fast sync with fallback
    hybrid_bus.configure_event(
        UINotificationEvent,
        PublishConfig(
            strategy=PublishStrategy.HYBRID_FAST,
            scope=EventScope.INTRA_BC,
            timeout_ms=50
        )
    )

    print("   ✅ Event strategies configured")

    # 3. Configure Bounded Context defaults
    print("\n🏗️ Configuring Bounded Context strategies...")

    hybrid_bus.configure_bounded_context(
        "orders",
        PublishStrategies.CRITICAL_HYBRID
    )

    hybrid_bus.configure_bounded_context(
        "inventory",
        PublishStrategies.INTER_BC_RELIABLE
    )

    hybrid_bus.configure_bounded_context(
        "frontend",
        PublishStrategies.INTRA_BC_FAST
    )

    print("   ✅ Bounded Context strategies configured")

    # 4. Demonstrate smart publishing
    print("\n📤 Smart Event Publishing Demo...")

    events_to_publish = [
        # Critical business event - will use hybrid reliable strategy
        OrderCreatedEvent(
            order_id="order-123",
            customer_id="customer-456",
            total_amount=299.99,
            occurred_at=datetime.now()
        ),

        # Fast intra-BC update - will use sync only
        OrderStatusUpdatedEvent(
            order_id="order-123",
            old_status="CREATED",
            new_status="CONFIRMED",
            occurred_at=datetime.now()
        ),

        # Inter-BC inventory - will use async only
        InventoryReservedEvent(
            product_id="product-789",
            quantity=2,
            reservation_id="res-101",
            occurred_at=datetime.now()
        ),

        # UI notification - will use hybrid fast
        UINotificationEvent(
            user_id="user-456",
            message="Your order has been confirmed",
            occurred_at=datetime.now()
        )
    ]

    # Publish events with smart routing
    for event in events_to_publish:
        print(f"\\n   Publishing: {event.__class__.__name__}")
        print(f"   BC: {event.bounded_context}")

        try:
            await hybrid_bus.publish(event)
            print(f"   ✅ Published successfully")
        except Exception as e:
            print(f"   ❌ Failed to publish: {e}")

    # 5. Show metrics
    print("\\n📊 Publishing Metrics...")
    metrics = await hybrid_bus.get_metrics()

    for key, value in metrics.items():
        print(f"   {key}: {value}")

    # 6. Show outbox contents
    print("\\n📦 Outbox Contents (Async Events)...")
    print(f"   Events in Outbox: {len(mock_outbox.events)}")

    for i, event_data in enumerate(mock_outbox.events, 1):
        topic = event_data["topic"]
        print(f"   {i}. {topic}")

    # 7. Demonstrate strategy override
    print("\\n🔄 Strategy Override Demo...")

    # Force a normally sync event to use async
    ui_event = UINotificationEvent(
        user_id="user-789",
        message="Force async notification",
        occurred_at=datetime.now()
    )

    print("   Forcing UI event to use async strategy...")
    await hybrid_bus.publish(
        ui_event,
        config=PublishConfig(strategy=PublishStrategy.ASYNC_ONLY)
    )

    print(f"   ✅ Override successful - Outbox now has {len(mock_outbox.events)} events")

    print("\\n" + "=" * 30)
    print("🎉 Hybrid Messaging Demo Completed!")

    print("\\n💡 Key Benefits Demonstrated:")
    print("   • Smart routing based on event type and BC")
    print("   • Performance optimization (sync for fast, async for reliable)")
    print("   • Flexibility through configuration")
    print("   • Circuit breaker fault tolerance")
    print("   • Comprehensive metrics and monitoring")

    # Cleanup
    await sync_bus.stop()


if __name__ == "__main__":
    asyncio.run(hybrid_messaging_demo())
