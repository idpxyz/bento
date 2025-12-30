"""
Simple E2E test to verify Outbox event persistence after order creation.

This test verifies:
1. Order aggregate is created with items
2. Domain events are tracked and persisted to Outbox table
3. Outbox events can be queried and have correct status
"""

import pytest
from bento.core.ids import ID
from sqlalchemy import text

from contexts.catalog.domain.models.product import Product
from contexts.ordering.application.commands.create_order import (
    CreateOrderCommand,
    CreateOrderHandler,
    OrderItemInput,
)
from contexts.ordering.domain.models.order import Order


@pytest.mark.asyncio
async def test_order_creation_persists_outbox_events(db_session):
    """Test that creating an order persists events to Outbox table."""
    from bento.persistence.outbox.record import SqlAlchemyOutbox
    from bento.persistence.uow import SQLAlchemyUnitOfWork as UnitOfWork

    # Create outbox for UoW
    outbox = SqlAlchemyOutbox(db_session)

    # Create a test product first
    product_id = str(ID.generate())
    product = Product(
        id=ID(product_id), name="Test Product", description="A test product", price=100.0
    )

    # Persist product using UoW (with repository registration)
    from contexts.catalog.infrastructure.repositories.product_repository_impl import (
        ProductRepository,
    )

    uow = UnitOfWork(db_session, outbox)
    uow.register_repository(Product, lambda s: ProductRepository(s))
    async with uow:
        product_repo = uow.repository(Product)
        await product_repo.save(product)
        await uow.commit()

    # Create order via use case
    from contexts.ordering.infrastructure.repositories.order_repository_impl import (
        OrderRepository,
    )

    # Create a mock product catalog service
    class MockProductCatalog:
        async def check_products_available(self, product_ids: list[str]):
            # Return all products as available
            return product_ids, []

    uow = UnitOfWork(db_session, outbox)
    uow.register_repository(Product, lambda s: ProductRepository(s))
    uow.register_repository(Order, lambda s: OrderRepository(s))

    # Register product catalog as a port
    from contexts.ordering.domain.ports.services import IProductCatalogService
    product_catalog = MockProductCatalog()
    uow.register_port(IProductCatalogService, lambda s: product_catalog)

    # Create observability provider (NoOp for testing)
    from bento.adapters.observability.noop import NoOpObservabilityProvider
    observability = NoOpObservabilityProvider()

    handler = CreateOrderHandler(uow, observability)

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
        order = await handler.handle(command)
        await uow.commit()

    order_id = order.id

    # Verify Outbox contains the event
    result = await db_session.execute(
        text(
            """
            SELECT id, aggregate_id, topic, status, payload
            FROM outbox
            WHERE aggregate_id = :order_id
            ORDER BY created_at DESC
            """
        ),
        {"order_id": str(order_id)},
    )
    outbox_events = result.fetchall()

    # Should have at least 1 event (OrderCreatedEvent)
    assert len(outbox_events) > 0, "No events found in Outbox"

    event = outbox_events[0]
    assert event.aggregate_id == str(order_id)
    assert event.topic == "order.created"  # topic 使用 snake_case 格式
    assert event.status == "NEW"
    assert "customer_id" in str(event.payload)
    assert "items" in str(event.payload)

    print(f"✅ Outbox event verified: {event.topic} (status={event.status})")


if __name__ == "__main__":
    # Run the test via pytest instead of standalone
    # (db_session is a pytest fixture, not directly importable)
    pytest.main([__file__, "-v"])
