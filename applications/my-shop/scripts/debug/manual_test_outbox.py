#!/usr/bin/env python3
"""
Manual test script to verify Outbox event persistence.

This script:
1. Creates a Product
2. Creates an Order with OrderItems
3. Verifies events are persisted to Outbox table with status NEW
4. Shows the complete event flow without running the API server

Run: uv run python applications/my-shop/manual_test_outbox.py
"""

import asyncio
import json
import sys
from pathlib import Path

# Bento framework imports (before path modification)
from bento.core.ids import ID
from bento.infrastructure.database import create_async_engine_from_config
from bento.persistence.outbox.record import SqlAlchemyOutbox
from bento.persistence.uow import SQLAlchemyUnitOfWork
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# Add application to path for local imports
sys.path.insert(0, str(Path(__file__).parent))

from contexts.catalog.domain.models.product import Product
from contexts.catalog.infrastructure.repositories.product_repository_impl import (
    ProductRepository,
)
from contexts.ordering.application.commands.create_order import (
    CreateOrderCommand,
    CreateOrderUseCase,
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


async def main():
    """Run manual Outbox verification test."""
    print("=" * 70)
    print("🧪 Manual Outbox Event Verification Test")
    print("=" * 70)

    # Initialize database with absolute path
    script_dir = Path(__file__).parent
    db_path = script_dir / "my_shop.db"

    from bento.infrastructure.database import DatabaseConfig

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
        name="Test Product for Outbox",
        description="Product created by manual test",
        price=150.0,
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

    # Step 2: Create order via use case
    print("\n2️⃣ Creating order with items...")
    customer_id = "test-customer-" + str(ID.generate())[:8]

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
                    product_name="Test Product for Outbox",
                    quantity=3,
                    unit_price=150.0,
                )
            ],
        )

        async with uow:
            order = await use_case.handle(command)
            await uow.commit()

        order_id = order.id
        total = order.total

    print(f"   ✅ Order created: {order_id}")
    print(f"   💰 Total: ${total:.2f}")
    print(f"   👤 Customer: {customer_id}")

    # Step 3: Query Outbox table
    print("\n3️⃣ Querying Outbox table...")
    async with session_factory() as session:
        result = await session.execute(
            text(
                """
                SELECT
                    id,
                    aggregate_id,
                    type,
                    status,
                    payload as payload_text,
                    created_at
                FROM outbox
                WHERE aggregate_id = :order_id
                ORDER BY created_at DESC
                """
            ),
            {"order_id": order_id},
        )
        outbox_events = result.fetchall()

    if not outbox_events:
        print("   ❌ ERROR: No events found in Outbox!")
        print("   This indicates events are not being persisted.")
        return 1

    print(f"   ✅ Found {len(outbox_events)} event(s) in Outbox")

    # Step 4: Display event details
    print("\n4️⃣ Event Details:")
    for idx, event in enumerate(outbox_events, 1):
        print(f"\n   Event #{idx}:")
        print(f"   - ID: {event.id}")
        print(f"   - Type: {event.type}")
        print(f"   - Status: {event.status}")
        print(f"   - Aggregate ID: {event.aggregate_id}")
        print(f"   - Created: {event.created_at}")

        # Parse and show key payload fields

        payload = json.loads(event.payload_text)
        print(f"   - Customer ID: {payload.get('customer_id')}")
        print(f"   - Total: ${payload.get('total', 0):.2f}")
        print(f"   - Item Count: {payload.get('item_count', 0)}")
        if "items" in payload:
            print(f"   - Items in Payload: {len(payload['items'])} item(s)")

    # Step 5: Verify status
    print("\n5️⃣ Verification Results:")
    all_new = all(e.status == "NEW" for e in outbox_events)
    all_correct_type = all(e.type == "OrderCreatedEvent" for e in outbox_events)

    if all_new and all_correct_type:
        print("   ✅ SUCCESS: Events persisted correctly!")
        print("   ✅ Status: NEW (ready for projection)")
        print("   ✅ Event Type: OrderCreatedEvent")
        print("\n   📋 Next: OutboxProjector will consume these events and mark as SENT")
        return 0
    else:
        print("   ⚠️  WARNING: Unexpected event state")
        if not all_new:
            print(
                f"   - Expected all events with status NEW, found: {set(e.status for e in outbox_events)}"
            )
        if not all_correct_type:
            print(
                f"   - Expected OrderCreatedEvent, found: {set(e.event_type for e in outbox_events)}"
            )
        return 1


if __name__ == "__main__":
    print()
    exit_code = asyncio.run(main())
    print("\n" + "=" * 70)
    if exit_code == 0:
        print("✅ Test PASSED - Outbox event persistence is working!")
    else:
        print("❌ Test FAILED - Check the output above")
    print("=" * 70)
    sys.exit(exit_code)
