"""Example: How to use the Outbox Pattern in Bento.

This example demonstrates:
1. How to define domain events
2. How to use the event registry
3. How to raise events from Aggregates
4. How to use UoW with Outbox pattern
5. How to start the Projector
"""

from dataclasses import dataclass
from uuid import uuid4

from bento.domain import DomainEvent, register_event
from bento.persistence.uow import register_event_from_aggregate


# ==================== Step 1: Define Domain Events ====================


@register_event  # ✅ Register event for deserialization
@dataclass(frozen=True)
class OrderCreatedEvent(DomainEvent):
    """Event: A new order was created."""

    order_id: str = ""
    customer_id: str = ""
    total_amount: float = 0.0


@register_event
@dataclass(frozen=True)
class OrderCancelledEvent(DomainEvent):
    """Event: An order was cancelled."""

    order_id: str = ""
    reason: str = ""


# ==================== Step 2: Use Events in Aggregate Root ====================


class Order:
    """Order Aggregate Root."""

    def __init__(self, order_id: str, customer_id: str):
        self.order_id = order_id
        self.customer_id = customer_id
        self.total_amount = 0.0
        self.status = "PENDING"

    def create(self) -> None:
        """Create order and raise event."""
        self.status = "CREATED"

        # ✅ Raise event via ContextVar (no UoW dependency!)
        event = OrderCreatedEvent(
            event_id=uuid4(),
            name="OrderCreatedEvent",
            tenant_id="tenant-123",  # Multi-tenant support
            aggregate_id=self.order_id,  # Traceability
            order_id=self.order_id,
            customer_id=self.customer_id,
            total_amount=self.total_amount,
        )
        register_event_from_aggregate(event)

    def cancel(self, reason: str) -> None:
        """Cancel order and raise event."""
        self.status = "CANCELLED"

        event = OrderCancelledEvent(
            event_id=uuid4(),
            name="OrderCancelledEvent",
            tenant_id="tenant-123",
            aggregate_id=self.order_id,
            order_id=self.order_id,
            reason=reason,
        )
        register_event_from_aggregate(event)


# ==================== Step 3: Use UoW in Application Service ====================


async def create_order_use_case(
    session_factory,
    order_id: str,
    customer_id: str,
):
    """Application service: Create order."""
    from bento.persistence.sqlalchemy.outbox_sql import SqlAlchemyOutbox
    from bento.persistence.uow import SQLAlchemyUnitOfWork

    async with session_factory() as session:
        # Create UoW with Outbox
        outbox = SqlAlchemyOutbox(session)
        uow = SQLAlchemyUnitOfWork(
            session=session,
            outbox=outbox,
            # Optional: Add event_bus for dual publishing
            # event_bus=event_bus,
        )

        async with uow:
            # Create order
            order = Order(order_id=order_id, customer_id=customer_id)
            order.create()  # ✅ Events are automatically registered!

            # Save order (this is application-specific)
            # order_repo = uow.repository(Order)
            # await order_repo.save(order)

            # ✅ Commit: Events are automatically written to Outbox
            await uow.commit()

    # Done! Events are now in Outbox table, ready to be published


# ==================== Step 4: Start Outbox Projector ====================


async def start_projector_example():
    """Start Outbox Projector (in separate process/service)."""
    import asyncio

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from bento.infrastructure.projection.projector import OutboxProjector

    # Create database connection
    engine = create_async_engine("postgresql+asyncpg://user:pass@localhost/db")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    # Create Message Bus (implementation-specific)
    # from your_messaging_adapter import YourMessageBus
    # message_bus = YourMessageBus()

    # For this example, we'll use a mock
    class MockMessageBus:
        async def publish(self, events):
            print(f"Publishing {len(events)} events:")
            for event in events:
                print(f"  - {event.__class__.__name__}: {event}")

    message_bus = MockMessageBus()

    # Create Projector for each tenant (using default configuration)
    projector_tenant1 = OutboxProjector(
        session_factory=session_factory,
        message_bus=message_bus,  # type: ignore[arg-type]
        tenant_id="tenant-123"
        # config parameter omitted - will use default configuration from environment
    )

    # Start projector in background
    task = asyncio.create_task(projector_tenant1.run_forever())

    # Run until interrupted
    try:
        await task
    except asyncio.CancelledError:
        await projector_tenant1.stop()
        print("Projector stopped")


# ==================== Step 5: Complete Example ====================


async def complete_example():
    """Complete end-to-end example."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    # 1. Setup database
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    # Create tables
    from bento.persistence.sqlalchemy.base import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 2. Create order (events will be in Outbox)
    await create_order_use_case(
        session_factory=session_factory,
        order_id="order-123",
        customer_id="cust-456",
    )

    # 3. Verify events are in Outbox
    from sqlalchemy import select

    from bento.persistence.sqlalchemy.outbox_sql import OutboxRecord

    async with session_factory() as session:
        stmt = select(OutboxRecord).where(OutboxRecord.status == "NEW")
        result = await session.execute(stmt)
        records = result.scalars().all()

        print(f"\n✅ Found {len(records)} events in Outbox:")
        for record in records:
            print(f"  - {record.type} (id={record.id})")
            print(f"    Status: {record.status}")
            print(f"    Tenant: {record.tenant_id}")
            print(f"    Aggregate: {record.aggregate_id}")
            print(f"    Payload: {record.payload}")

    await engine.dispose()


# ==================== Main ====================

if __name__ == "__main__":
    import asyncio

    print("=" * 60)
    print("Bento Outbox Pattern Example")
    print("=" * 60)

    asyncio.run(complete_example())

    print("\n✅ Example completed!")
    print("\nKey points:")
    print("1. Events are registered via @register_event decorator")
    print("2. Aggregates raise events via register_event_from_aggregate()")
    print("3. UoW automatically persists events to Outbox (via Event Listener)")
    print("4. Projector asynchronously publishes events from Outbox")
    print("5. Multi-tenant support built-in (tenant_id)")
