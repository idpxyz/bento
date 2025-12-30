#!/usr/bin/env python3
"""
End-to-end Outbox flow test with background worker running.

This script verifies the complete Outbox pattern with the running application:
1. Creates a new order (generates NEW event)
2. Monitors the event status in real-time
3. Shows how the background OutboxProjector consumes it
4. Verifies event transitions from NEW → SENT

Run: uv run python applications/my-shop/test_outbox_end_to_end.py
"""

import asyncio
import sys
from pathlib import Path

# Bento framework imports
from bento.core.ids import ID
from bento.infrastructure.database import DatabaseConfig, create_async_engine_from_config
from bento.persistence.outbox.record import SqlAlchemyOutbox
from bento.persistence.uow import SQLAlchemyUnitOfWork
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# Add application to path
sys.path.insert(0, str(Path(__file__).parent))

from contexts.catalog.domain.models.product import Product
from contexts.catalog.infrastructure.repositories.product_repository_impl import (
    ProductRepository,
)
from contexts.ordering.application.commands.create_order import (
    CreateOrderCommand,
    CreateOrderHandler,
    OrderItemInput,
)
from contexts.ordering.domain.models.order import Order
from contexts.ordering.infrastructure.repositories.order_repository_impl import (
    OrderRepository,
)


def register_repositories(uow: SQLAlchemyUnitOfWork) -> None:
    """Register all required repositories to UnitOfWork."""
    uow.register_repository(Product, lambda s: ProductRepository(s))
    uow.register_repository(Order, lambda s: OrderRepository(s))


async def check_event_status(session_factory, event_id: str) -> dict:
    """Check the status of an event in Outbox."""
    async with session_factory() as session:
        result = await session.execute(
            text(
                """
                SELECT id, type, status, created_at
                FROM outbox
                WHERE id = :event_id
                """
            ),
            {"event_id": event_id},
        )
        row = result.fetchone()
        if row:
            return {
                "id": row.id,
                "type": row.type,
                "status": row.status,
                "created_at": row.created_at,
            }
        return None


async def main():
    """Test end-to-end Outbox flow with background worker."""
    print("=" * 70)
    print("🧪 End-to-End Outbox Flow Test (with Background Worker)")
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

    # Step 1: Create a test product
    print("\n1️⃣ Creating test product...")
    product_id = str(ID.generate())
    product = Product(
        id=product_id,
        name="Test Product for E2E",
        description="Product created by E2E test",
        price=200.0,
    )

    async with session_factory() as session:
        outbox = SqlAlchemyOutbox(session)
        uow = SQLAlchemyUnitOfWork(session, outbox)
        register_repositories(uow)
        async with uow:
            product_repo = uow.repository(Product)
            await product_repo.save(product)
            await uow.commit()

    print(f"   ✅ Product created: {product_id}")

    # Step 2: Create order and capture event ID
    print("\n2️⃣ Creating order (this will generate Outbox event)...")
    customer_id = "e2e-customer-" + str(ID.generate())[:8]

    event_id = None
    async with session_factory() as session:
        outbox = SqlAlchemyOutbox(session)
        uow = SQLAlchemyUnitOfWork(session, outbox)
        register_repositories(uow)

        # Create observability provider (NoOp for testing)
        from bento.adapters.observability.noop import NoOpObservabilityProvider

        observability = NoOpObservabilityProvider()

        handler = CreateOrderHandler(uow, observability)

        command = CreateOrderCommand(
            customer_id=customer_id,
            items=[
                OrderItemInput(
                    product_id=product_id,
                    product_name="Test Product for E2E",
                    quantity=2,
                    unit_price=200.0,
                )
            ],
        )

        async with uow:
            order = await handler.handle(command)
            await uow.commit()

        order_id = order.id

        # Get the event ID that was just created
        result = await session.execute(
            text(
                """
                SELECT id FROM outbox
                WHERE aggregate_id = :order_id
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"order_id": order_id},
        )
        row = result.fetchone()
        if row:
            event_id = row.id

    print(f"   ✅ Order created: {order_id}")
    print("   💰 Total: $400.00")
    print(f"   📝 Event ID: {event_id}")

    # Step 3: Monitor event status in real-time
    print("\n3️⃣ Monitoring event status (background worker should consume it)...")
    print("   🕐 Checking every 0.5 seconds for up to 5 seconds...")

    initial_status = await check_event_status(session_factory, event_id)
    if initial_status:
        print(f"\n   Initial status: {initial_status['status']}")

    max_checks = 10
    for i in range(max_checks):
        await asyncio.sleep(0.5)

        status_info = await check_event_status(session_factory, event_id)
        if not status_info:
            print("   ❌ Event not found!")
            break

        current_status = status_info["status"]
        print(f"   Check #{i + 1}: Status = {current_status}", end="")

        if current_status == "SENT":
            print(" ✅ (Consumed by background worker!)")
            break
        elif current_status == "NEW":
            print(" ⏳ (Waiting...)")
        else:
            print(f" ⚠️  (Unexpected: {current_status})")

    # Step 4: Final verification
    print("\n4️⃣ Final Verification:")
    final_status = await check_event_status(session_factory, event_id)

    if final_status and final_status["status"] == "SENT":
        print("   ✅ SUCCESS: Event was consumed by background OutboxProjector!")
        print("   ✅ Status: NEW → SENT")
        print(f"   ✅ Created at: {final_status['created_at']}")
        print("\n   📋 This proves the complete Outbox pattern is working:")
        print("      1. Domain event generated ✓")
        print("      2. Event persisted to Outbox ✓")
        print("      3. Background worker consumed it ✓")
        print("      4. Event status updated to SENT ✓")
        return 0
    else:
        print("   ⚠️  Event was not consumed within timeout")
        print(f"   Current status: {final_status['status'] if final_status else 'Unknown'}")
        print("\n   💡 The background worker might be slow or not running")
        return 1


if __name__ == "__main__":
    print()
    exit_code = asyncio.run(main())
    print("\n" + "=" * 70)
    if exit_code == 0:
        print("✅ Test PASSED - Complete Outbox flow is working!")
    else:
        print("⚠️  Test did not complete as expected")
    print("=" * 70)
    sys.exit(exit_code)
