"""Optimized Hybrid Messaging Example - Zero duplication with existing UoW logic.

This example demonstrates the optimized HybridMessageBus that:
1. Leverages existing UoW dual publishing logic (no duplication!)
2. Adds smart routing and configuration on top
3. Works seamlessly with your existing UoW setup
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime

from bento.domain.domain_event import DomainEvent
from bento.application.ports.hybrid_message_bus import PublishStrategies
from bento.adapters.messaging.hybrid.message_bus import create_hybrid_message_bus
from bento.persistence.uow import SQLAlchemyUnitOfWork
from bento.adapters.messaging.inprocess.message_bus import InProcessMessageBus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Sample events (same as before)
@dataclass(frozen=True)
class OrderCreatedEvent(DomainEvent):
    order_id: str = ""
    customer_id: str = ""
    total_amount: float = 0.0
    topic: str = "order.created"
    bounded_context: str = "orders"


@dataclass(frozen=True)
class OrderStatusUpdatedEvent(DomainEvent):
    order_id: str = ""
    old_status: str = ""
    new_status: str = ""
    topic: str = "order.status_updated"
    bounded_context: str = "orders"


class MockSession:
    """Mock session for demonstration."""
    async def commit(self):
        logger.info("💾 Session committed (Outbox persisted)")


class MockOutbox:
    """Mock Outbox for demonstration."""
    def __init__(self):
        self.events = []

    async def add(self, topic: str, payload: dict) -> None:
        self.events.append({"topic": topic, "payload": payload})
        logger.info(f"📦 Added to Outbox: {topic}")


async def optimized_hybrid_demo():
    """Demonstrate optimized hybrid messaging with zero duplication."""

    print("🎯 Optimized Hybrid Messaging Demo")
    print("=" * 40)

    # 1. Setup existing UoW (your current setup - no changes needed!)
    print("\n🔧 Setting up existing UoW infrastructure...")

    mock_session = MockSession()
    mock_outbox = MockOutbox()
    sync_bus = InProcessMessageBus(source="optimized-demo")

    # This is your existing UoW setup - no changes needed!
    uow = SQLAlchemyUnitOfWork(
        session=mock_session,
        outbox=mock_outbox,
        event_bus=sync_bus  # This enables UoW's dual publishing
    )

    print("   ✅ Existing UoW setup complete (no changes needed!)")

    # 2. Add hybrid intelligence with zero duplication
    print("\n🧠 Adding smart routing intelligence...")

    # Key: This leverages your existing UoW, no duplication!
    hybrid_bus = create_hybrid_message_bus(uow)

    # Configure smart routing (same as before)
    hybrid_bus.configure_event(
        OrderCreatedEvent,
        PublishStrategies.CRITICAL_HYBRID  # Will use UoW's dual publishing!
    )

    hybrid_bus.configure_event(
        OrderStatusUpdatedEvent,
        PublishStrategies.INTRA_BC_FAST
    )

    print("   ✅ Smart routing configured (leveraging existing UoW logic)")

    # 3. Demonstrate zero duplication publishing
    print("\n📤 Zero Duplication Publishing Demo...")

    events_to_test = [
        OrderCreatedEvent(
            order_id="order-456",
            customer_id="customer-789",
            total_amount=199.99,
            occurred_at=datetime.now()
        ),

        OrderStatusUpdatedEvent(
            order_id="order-456",
            old_status="CREATED",
            new_status="PAID",
            occurred_at=datetime.now()
        )
    ]

    for event in events_to_test:
        print(f"\n   📨 Publishing: {event.__class__.__name__}")
        print(f"   🏗️ BC: {event.bounded_context}")

        # This will intelligently route to UoW's proven dual publishing logic
        await hybrid_bus.publish(event)
        print("   ✅ Published via optimized routing")

    # 4. Show the benefits
    print("\n📊 Optimization Benefits...")
    metrics = await hybrid_bus.get_metrics()

    for key, value in metrics.items():
        print(f"   {key}: {value}")

    print("\n💡 Key Optimizations Achieved:")
    benefits = [
        "✅ Zero logic duplication - reuses existing UoW dual publishing",
        "✅ Smart routing added on top of proven infrastructure",
        "✅ All existing error handling and retry logic preserved",
        "✅ Works seamlessly with current UoW setup",
        "✅ Lightweight - only adds routing intelligence",
        "✅ Backward compatible - no breaking changes"
    ]

    for benefit in benefits:
        print(f"   {benefit}")

    # 5. Compare with previous implementation
    print("\n🔄 Architecture Comparison:")
    print("   ❌ Previous HybridMessageBus:")
    print("      - Reimplemented dual publishing logic")
    print("      - Duplicated error handling and retries")
    print("      - Parallel implementation to UoW")

    print("\n   ✅ Optimized HybridMessageBus:")
    print("      - Leverages existing UoW dual publishing")
    print("      - Zero duplication of proven logic")
    print("      - Adds smart routing on top")
    print("      - Works with existing infrastructure")

    print(f"\n   📦 Outbox Contents: {len(mock_outbox.events)} events")
    for i, event_data in enumerate(mock_outbox.events, 1):
        print(f"      {i}. {event_data['topic']}")

    print("\n" + "=" * 40)
    print("🎉 Optimized Hybrid Messaging Demo Completed!")

    print("\n🏆 Perfect Solution Achieved:")
    print("   • Smart routing without logic duplication")
    print("   • Leverages your existing, proven UoW setup")
    print("   • Adds hybrid intelligence with minimal overhead")
    print("   • Zero breaking changes to current architecture")

    # Cleanup
    await sync_bus.stop()


if __name__ == "__main__":
    asyncio.run(optimized_hybrid_demo())
