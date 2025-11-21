#!/usr/bin/env python3
"""
Test OutboxProjector consumption flow.

This script verifies:
1. OutboxProjector reads NEW events from Outbox table
2. Events are published to InProcessMessageBus
3. Event status is updated from NEW → SENT
4. Event handlers receive and process the events

Run: uv run python applications/my-shop/test_outbox_projector.py
"""

import asyncio
import sys
from pathlib import Path

# Bento framework imports
from bento.domain.domain_event import DomainEvent
from bento.infrastructure.database import DatabaseConfig, create_async_engine_from_config
from bento.infrastructure.projection.projector import OutboxProjector
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# Add application to path
sys.path.insert(0, str(Path(__file__).parent))


# Import InProcessMessageBus
from bento.adapters.messaging.inprocess import InProcessMessageBus

# Import domain events for registration
from contexts.ordering.domain.events.ordercreated_event import OrderCreatedEvent


class TestEventHandler:
    """Test event handler to verify events are received."""

    def __init__(self):
        self.received_events = []

    async def handle(self, event: DomainEvent):
        """Handle received events."""
        print(f"   📨 Handler received: {event.__class__.__name__}")
        print(f"      - Aggregate ID: {event.aggregate_id}")
        if isinstance(event, OrderCreatedEvent):
            print(f"      - Customer ID: {event.customer_id}")
            print(f"      - Total: ${event.total:.2f}")
            print(f"      - Item Count: {event.item_count}")
        self.received_events.append(event)


async def main():
    """Test OutboxProjector consumption flow."""
    print("=" * 70)
    print("🧪 OutboxProjector Consumption Test")
    print("=" * 70)

    # Setup database
    script_dir = Path(__file__).parent
    db_path = script_dir / "my_shop.db"
    db_config = DatabaseConfig(
        url=f"sqlite+aiosqlite:///{db_path.absolute()}",
        echo=False,
    )
    print(f"\n📂 Using database: {db_path.absolute()}")

    engine = create_async_engine_from_config(db_config)
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    # Step 1: Check for NEW events in Outbox
    print("\n1️⃣ Checking Outbox for NEW events...")
    async with session_factory() as session:
        result = await session.execute(
            text(
                """
                SELECT id, aggregate_id, type, status
                FROM outbox
                WHERE status = 'NEW'
                ORDER BY created_at ASC
                LIMIT 5
                """
            )
        )
        new_events = result.fetchall()

    if not new_events:
        print("   ⚠️  No NEW events found in Outbox")
        print("   💡 Run manual_test_outbox.py first to create test events")
        return 1

    print(f"   ✅ Found {len(new_events)} NEW event(s) in Outbox:")
    for event in new_events:
        print(f"      - {event.type} (ID: {event.id[:8]}...)")

    # Step 2: Setup InProcessMessageBus with test handler
    print("\n2️⃣ Setting up InProcessMessageBus with test handler...")
    bus = InProcessMessageBus(source="test")
    handler = TestEventHandler()

    # Subscribe handler to OrderCreatedEvent
    await bus.subscribe(OrderCreatedEvent, handler.handle)
    print("   ✅ Test handler subscribed to OrderCreatedEvent")

    # Step 3: Create and run OutboxProjector
    print("\n3️⃣ Starting OutboxProjector...")
    projector = OutboxProjector(
        session_factory=session_factory,
        message_bus=bus,
        batch_size=10,
        poll_interval_seconds=1,
    )

    print("   ✅ OutboxProjector created")
    print("   🔄 Running one projection cycle...")

    # Run one projection cycle
    try:
        await projector.project_once()
        print("   ✅ Projection cycle completed")
    except Exception as e:
        print(f"   ❌ Projection failed: {e}")
        import traceback

        traceback.print_exc()
        return 1

    # Give async handlers time to process
    await asyncio.sleep(0.5)

    # Step 4: Verify events were handled
    print("\n4️⃣ Verifying event handling...")
    if handler.received_events:
        print(f"   ✅ Handler received {len(handler.received_events)} event(s)")
        for idx, event in enumerate(handler.received_events, 1):
            print(f"      #{idx}: {event.__class__.__name__}")
    else:
        print("   ⚠️  No events received by handler")

    # Step 5: Check Outbox status updates
    print("\n5️⃣ Checking Outbox status updates...")
    event_ids = [e.id for e in new_events]

    async with session_factory() as session:
        placeholders = ",".join([f":id{i}" for i in range(len(event_ids))])
        params = {f"id{i}": event_id for i, event_id in enumerate(event_ids)}

        result = await session.execute(
            text(f"""
                SELECT id, type, status, published_at
                FROM outbox
                WHERE id IN ({placeholders})
            """),
            params,
        )
        updated_events = result.fetchall()

    sent_count = sum(1 for e in updated_events if e.status == "SENT")
    new_count = sum(1 for e in updated_events if e.status == "NEW")

    print("   📊 Status summary:")
    print(f"      - SENT: {sent_count}")
    print(f"      - NEW: {new_count}")

    if sent_count > 0:
        print("\n   ✅ Events successfully marked as SENT!")
        for event in updated_events:
            if event.status == "SENT":
                print(f"      - {event.type} → SENT (published: {event.published_at})")

    # Step 6: Final verification
    print("\n6️⃣ Final Verification:")

    success = True
    if sent_count == 0:
        print("   ❌ FAIL: No events were marked as SENT")
        success = False
    else:
        print(f"   ✅ PASS: {sent_count} event(s) marked as SENT")

    if len(handler.received_events) == 0:
        print("   ❌ FAIL: No events received by handler")
        success = False
    else:
        print(f"   ✅ PASS: {len(handler.received_events)} event(s) received by handler")

    if success:
        print("\n   🎉 OutboxProjector consumption flow works correctly!")
        print("   📋 Events flow: Outbox (NEW) → MessageBus → Handler → Outbox (SENT)")
        return 0
    else:
        print("\n   ⚠️  Some checks failed - review output above")
        return 1


if __name__ == "__main__":
    print()
    exit_code = asyncio.run(main())
    print("\n" + "=" * 70)
    if exit_code == 0:
        print("✅ Test PASSED - OutboxProjector is working correctly!")
    else:
        print("❌ Test FAILED - Check the output above")
    print("=" * 70)
    sys.exit(exit_code)
