"""
Simple E2E test to verify Outbox event persistence after order creation.

This test verifies:
1. Order aggregate is created with items
2. Domain events are tracked and persisted to Outbox table
3. Outbox events can be queried and have correct status
"""

import asyncio

import pytest
from bento.core.ids import ID
from sqlalchemy import text

from contexts.catalog.domain.product import Product
from contexts.ordering.application.commands.create_order import (
    CreateOrderCommand,
    CreateOrderUseCase,
    OrderItemInput,
)


@pytest.mark.asyncio
async def test_order_creation_persists_outbox_events(db_session):
    """Test that creating an order persists events to Outbox table."""
    from bento.persistence.uow import SQLAlchemyUnitOfWork as UnitOfWork

    # Create a test product first
    product_id = str(ID.generate())
    product = Product(
        id=ID(product_id), name="Test Product", description="A test product", price=100.0
    )

    # Persist product using UoW
    async with db_session() as session:
        uow = UnitOfWork(session)
        async with uow:
            product_repo = uow.repository(Product)
            await product_repo.save(product)
            await uow.commit()

    # Create order via use case
    async with db_session() as session:
        uow = UnitOfWork(session)
        use_case = CreateOrderUseCase(uow)

        command = CreateOrderCommand(
            customer_id="test-customer-123",
            items=[
                OrderItemInput(
                    product_id=product_id,
                    product_name="Test Product",
                    quantity=2,
                    unit_price=100.0,
                )
            ],
        )

        async with uow:
            order = await use_case.handle(command)
            await uow.commit()

        order_id = order.id

    # Verify Outbox contains the event
    async with db_session() as session:
        result = await session.execute(
            text(
                """
                SELECT id, aggregate_id, event_type, status, payload
                FROM outbox
                WHERE aggregate_id = :order_id
                ORDER BY created_at DESC
                """
            ),
            {"order_id": order_id},
        )
        outbox_events = result.fetchall()

        # Should have at least 1 event (OrderCreatedEvent)
        assert len(outbox_events) > 0, "No events found in Outbox"

        event = outbox_events[0]
        assert event.aggregate_id == order_id
        assert event.event_type == "OrderCreatedEvent"
        assert event.status == "NEW"
        assert "customer_id" in event.payload
        assert "items" in event.payload

        print(f"✅ Outbox event verified: {event.event_type} (status={event.status})")


if __name__ == "__main__":
    # Run the test standalone
    from tests.conftest import db_session

    asyncio.run(test_order_creation_persists_outbox_events(db_session))
