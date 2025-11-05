"""Integration tests for Outbox Pattern.

This test suite verifies the complete Outbox pattern flow:
1. Event registration from Aggregate
2. Automatic Outbox persistence via Event Listener
3. Event projection and publishing via Projector
"""

from dataclasses import dataclass
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import String, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bento.application.ports.message_bus import MessageBus
from bento.domain.domain_event import DomainEvent
from bento.domain.event_registry import register_event
from bento.infrastructure.projection.projector import OutboxProjector
from bento.persistence.sqlalchemy.outbox_sql import OutboxRecord, SqlAlchemyOutbox
from bento.persistence.uow import SQLAlchemyUnitOfWork, register_event_from_aggregate

# ==================== Test Events ====================


# Define events BEFORE registration to allow proper import
@dataclass(frozen=True)
class OrderCreatedEvent(DomainEvent):
    """Test event: Order created."""

    order_id: str = ""
    customer_id: str = ""
    total_amount: float = 0.0


@dataclass(frozen=True)
class OrderCancelledEvent(DomainEvent):
    """Test event: Order cancelled."""

    order_id: str = ""
    reason: str = ""


# Register events (only once at module import)
register_event(OrderCreatedEvent)
register_event(OrderCancelledEvent)


# ==================== Mock MessageBus ====================


class MockMessageBus(MessageBus):
    """Mock MessageBus for testing Projector."""

    def __init__(self):
        self.published_events: list[DomainEvent] = []
        self.should_fail = False
        self.fail_count = 0

    async def publish(self, events: list[DomainEvent]) -> None:
        """Mock publish - stores events instead of sending them."""
        if self.should_fail:
            self.fail_count += 1
            raise RuntimeError(f"Mock publish failure #{self.fail_count}")

        self.published_events.extend(events)

    def reset(self):
        """Reset mock state."""
        self.published_events.clear()
        self.should_fail = False
        self.fail_count = 0


# ==================== Test Fixtures ====================


@pytest_asyncio.fixture
async def engine():
    """Create in-memory SQLite database for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    # Create tables
    from sqlalchemy import JSON

    from bento.persistence.sqlalchemy.base import Base
    from bento.persistence.sqlalchemy.outbox_sql import OutboxRecord

    # SQLite doesn't support JSONB and UUID natively, so we need to replace them for testing
    # This is a test-only modification
    if engine.dialect.name == "sqlite":
        # Replace JSONB with JSON for SQLite compatibility
        OutboxRecord.__table__.columns["payload"].type = JSON()
        # Replace UUID with String for SQLite compatibility
        OutboxRecord.__table__.columns["id"].type = String(36)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
def session_factory(engine):
    """Create session factory."""
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def session(session_factory):
    """Create test session."""
    async with session_factory() as session:
        yield session


# ==================== Tests ====================


@pytest.mark.asyncio
async def test_event_registration_via_context_var(session_factory):
    """Test that events are registered via ContextVar."""
    # Import listener to register it
    import bento.persistence.sqlalchemy.outbox_listener  # noqa: F401

    # Create event
    event = OrderCreatedEvent(
        event_id=uuid4(),
        name="OrderCreatedEvent",
        tenant_id="test-tenant",
        aggregate_id="order-123",
        order_id="order-123",
        customer_id="cust-456",
        total_amount=99.99,
    )

    # Create UoW
    async with session_factory() as session:
        outbox = SqlAlchemyOutbox(session)
        uow = SQLAlchemyUnitOfWork(session, outbox)

        async with uow:
            # Register event via ContextVar
            register_event_from_aggregate(event)

            # Verify event is in pending_events
            assert len(uow.pending_events) == 1
            assert uow.pending_events[0] == event

            # Commit triggers flush which triggers after_flush listener
            await uow.commit()

    # Verify event is in Outbox
    async with session_factory() as session:
        # SQLite stores UUID as String, so convert for comparison
        event_id_str = str(event.event_id)
        stmt = select(OutboxRecord).where(OutboxRecord.id == event_id_str)
        result = await session.execute(stmt)
        outbox_record = result.scalar_one_or_none()

        assert outbox_record is not None, f"Event {event_id_str} not found in Outbox"
        assert outbox_record.type == "OrderCreatedEvent"
        assert outbox_record.tenant_id == "test-tenant"
        assert outbox_record.aggregate_id == "order-123"
        assert outbox_record.status == "NEW"
        assert outbox_record.payload["order_id"] == "order-123"
        assert outbox_record.payload["customer_id"] == "cust-456"


@pytest.mark.asyncio
async def test_outbox_listener_automatic_persistence(session_factory):
    """Test that Event Listener automatically persists events to Outbox."""
    # Import listener to register it
    import bento.persistence.sqlalchemy.outbox_listener  # noqa: F401

    # Create multiple events
    events = [
        OrderCreatedEvent(
            event_id=uuid4(),
            name="OrderCreatedEvent",
            tenant_id="test-tenant",
            order_id=f"order-{i}",
            customer_id=f"cust-{i}",
            total_amount=float(i * 10),
        )
        for i in range(3)
    ]

    # Register events via UoW
    async with session_factory() as session:
        outbox = SqlAlchemyOutbox(session)
        uow = SQLAlchemyUnitOfWork(session, outbox)

        async with uow:
            for event in events:
                register_event_from_aggregate(event)

            await uow.commit()

    # Verify all events are in Outbox
    async with session_factory() as session:
        stmt = select(OutboxRecord).where(OutboxRecord.status == "NEW")
        result = await session.execute(stmt)
        records = result.scalars().all()

        assert len(records) == 3
        for record in records:
            assert record.type == "OrderCreatedEvent"
            assert record.status == "NEW"


@pytest.mark.asyncio
async def test_outbox_idempotency(session_factory):
    """Test that duplicate events are not persisted (idempotency)."""
    # Import listener
    import bento.persistence.sqlalchemy.outbox_listener  # noqa: F401

    # Create event with fixed ID
    event_id = uuid4()
    event = OrderCreatedEvent(
        event_id=event_id,
        name="OrderCreatedEvent",
        tenant_id="test-tenant",
        order_id="order-123",
        customer_id="cust-456",
        total_amount=99.99,
    )

    # Register event twice
    for _ in range(2):
        async with session_factory() as session:
            outbox = SqlAlchemyOutbox(session)
            uow = SQLAlchemyUnitOfWork(session, outbox)

            async with uow:
                register_event_from_aggregate(event)
                await uow.commit()

    # Verify only one record exists
    async with session_factory() as session:
        event_id_str = str(event_id)
        stmt = select(OutboxRecord).where(OutboxRecord.id == event_id_str)
        result = await session.execute(stmt)
        records = result.scalars().all()

        assert len(records) == 1


@pytest.mark.asyncio
async def test_event_deserialization(session_factory):
    """Test that events can be deserialized from Outbox."""
    from bento.domain.event_registry import deserialize_event

    # Create and persist event
    original_event = OrderCreatedEvent(
        event_id=uuid4(),
        name="OrderCreatedEvent",
        tenant_id="test-tenant",
        aggregate_id="order-123",
        order_id="order-123",
        customer_id="cust-456",
        total_amount=99.99,
    )

    # Manually create Outbox record
    async with session_factory() as session:
        record = OutboxRecord.from_domain_event(original_event)
        session.add(record)
        await session.commit()

        # Read back
        event_id_str = str(original_event.event_id)
        stmt = select(OutboxRecord).where(OutboxRecord.id == event_id_str)
        result = await session.execute(stmt)
        saved_record = result.scalar_one()

        # Deserialize
        deserialized_event = deserialize_event(
            event_type=saved_record.type,
            payload=saved_record.payload,
        )

        # Verify
        assert isinstance(deserialized_event, OrderCreatedEvent)
        assert deserialized_event.event_id == original_event.event_id
        assert deserialized_event.order_id == original_event.order_id
        assert deserialized_event.customer_id == original_event.customer_id
        assert deserialized_event.total_amount == original_event.total_amount


@pytest.mark.asyncio
async def test_rollback_clears_events(session_factory):
    """Test that rollback clears pending events."""
    event = OrderCreatedEvent(
        event_id=uuid4(),
        name="OrderCreatedEvent",
        order_id="order-123",
        customer_id="cust-456",
        total_amount=99.99,
    )

    async with session_factory() as session:
        outbox = SqlAlchemyOutbox(session)
        uow = SQLAlchemyUnitOfWork(session, outbox)

        async with uow:
            register_event_from_aggregate(event)
            assert len(uow.pending_events) == 1

            await uow.rollback()

            # Events should be cleared
            assert len(uow.pending_events) == 0

    # Verify no events in Outbox
    async with session_factory() as session:
        stmt = select(OutboxRecord)
        result = await session.execute(stmt)
        records = result.scalars().all()

        assert len(records) == 0


# ==================== Projector Tests ====================


@pytest.mark.asyncio
async def test_projector_publishes_events(session_factory):
    """Test that Projector reads from Outbox and publishes events."""
    # Create and persist events to Outbox
    events = [
        OrderCreatedEvent(
            event_id=uuid4(),
            name="OrderCreatedEvent",
            tenant_id="test-tenant",
            aggregate_id=f"order-{i}",  # Add aggregate_id
            order_id=f"order-{i}",
            customer_id=f"cust-{i}",
            total_amount=float(i * 10),
        )
        for i in range(3)
    ]

    async with session_factory() as session:
        for event in events:
            record = OutboxRecord.from_domain_event(event)
            session.add(record)
        await session.commit()

    # Create Projector with MockMessageBus
    mock_bus = MockMessageBus()
    projector = OutboxProjector(
        session_factory=session_factory,
        message_bus=mock_bus,
        tenant_id="test-tenant",
        batch_size=10,
    )

    # Process all events
    count = await projector.publish_all()

    # Verify events were published
    assert count >= 3  # May be batch_size if batch was full
    assert len(mock_bus.published_events) == 3

    # Verify published events match original events
    published_order_ids = {evt.order_id for evt in mock_bus.published_events}
    expected_order_ids = {f"order-{i}" for i in range(3)}
    assert published_order_ids == expected_order_ids

    # Verify events are marked as SENT in database
    async with session_factory() as session:
        stmt = select(OutboxRecord).where(OutboxRecord.tenant_id == "test-tenant")
        result = await session.execute(stmt)
        records = result.scalars().all()

        assert len(records) == 3
        for record in records:
            assert record.status == "SENT"


@pytest.mark.asyncio
async def test_projector_handles_publish_failure(session_factory):
    """Test that Projector retries on publish failure."""
    # Create event
    event = OrderCreatedEvent(
        event_id=uuid4(),
        name="OrderCreatedEvent",
        tenant_id="test-tenant",
        order_id="order-123",
        customer_id="cust-456",
        total_amount=99.99,
    )

    async with session_factory() as session:
        record = OutboxRecord.from_domain_event(event)
        session.add(record)
        await session.commit()

    # Create Projector with failing MockMessageBus
    mock_bus = MockMessageBus()
    mock_bus.should_fail = True

    projector = OutboxProjector(
        session_factory=session_factory,
        message_bus=mock_bus,
        tenant_id="test-tenant",
        batch_size=10,
    )

    # Try to process - should fail
    await projector._process_once()

    # Verify event is still in NEW status (will retry)
    async with session_factory() as session:
        stmt = select(OutboxRecord).where(OutboxRecord.tenant_id == "test-tenant")
        result = await session.execute(stmt)
        record = result.scalar_one()

        assert record.status == "NEW"
        assert record.retry_cnt == 1  # Incremented


@pytest.mark.asyncio
async def test_projector_max_retry_marks_error(session_factory):
    """Test that Projector marks event as ERR after max retries."""
    # Create event with retry_cnt close to max
    event = OrderCreatedEvent(
        event_id=uuid4(),
        name="OrderCreatedEvent",
        tenant_id="test-tenant",
        order_id="order-123",
        customer_id="cust-456",
        total_amount=99.99,
    )

    async with session_factory() as session:
        record = OutboxRecord.from_domain_event(event)
        record.retry_cnt = 4  # One away from MAX_RETRY (5)
        session.add(record)
        await session.commit()

    # Create Projector with failing MockMessageBus
    mock_bus = MockMessageBus()
    mock_bus.should_fail = True

    projector = OutboxProjector(
        session_factory=session_factory,
        message_bus=mock_bus,
        tenant_id="test-tenant",
        batch_size=10,
    )

    # Process - should mark as ERR after hitting max retries
    await projector._process_once()

    # Verify event is marked as ERR
    async with session_factory() as session:
        stmt = select(OutboxRecord).where(OutboxRecord.tenant_id == "test-tenant")
        result = await session.execute(stmt)
        record = result.scalar_one()

        assert record.status == "ERR"
        assert record.retry_cnt == 5


@pytest.mark.asyncio
async def test_projector_multi_tenant_isolation(session_factory):
    """Test that Projector only processes events for its tenant."""
    # Create events for different tenants
    tenant1_event = OrderCreatedEvent(
        event_id=uuid4(),
        name="OrderCreatedEvent",
        tenant_id="tenant1",
        order_id="order-t1",
        customer_id="cust-1",
        total_amount=100.0,
    )

    tenant2_event = OrderCreatedEvent(
        event_id=uuid4(),
        name="OrderCreatedEvent",
        tenant_id="tenant2",
        order_id="order-t2",
        customer_id="cust-2",
        total_amount=200.0,
    )

    async with session_factory() as session:
        session.add(OutboxRecord.from_domain_event(tenant1_event))
        session.add(OutboxRecord.from_domain_event(tenant2_event))
        await session.commit()

    # Create Projector for tenant1 only
    mock_bus = MockMessageBus()
    projector = OutboxProjector(
        session_factory=session_factory,
        message_bus=mock_bus,
        tenant_id="tenant1",
        batch_size=10,
    )

    # Process all events
    await projector.publish_all()

    # Verify only tenant1 event was published
    assert len(mock_bus.published_events) == 1
    assert mock_bus.published_events[0].order_id == "order-t1"

    # Verify tenant1 event is SENT, tenant2 is still NEW
    async with session_factory() as session:
        stmt1 = select(OutboxRecord).where(OutboxRecord.tenant_id == "tenant1")
        result1 = await session.execute(stmt1)
        record1 = result1.scalar_one()
        assert record1.status == "SENT"

        stmt2 = select(OutboxRecord).where(OutboxRecord.tenant_id == "tenant2")
        result2 = await session.execute(stmt2)
        record2 = result2.scalar_one()
        assert record2.status == "NEW"  # Not processed


@pytest.mark.asyncio
async def test_end_to_end_outbox_pattern(session_factory):
    """Test complete end-to-end Outbox pattern flow."""
    # Step 1: Create event via UoW (simulating aggregate operation)
    event = OrderCreatedEvent(
        event_id=uuid4(),
        name="OrderCreatedEvent",
        tenant_id="test-tenant",
        aggregate_id="order-999",
        order_id="order-999",
        customer_id="cust-999",
        total_amount=999.99,
    )

    async with session_factory() as session:
        outbox = SqlAlchemyOutbox(session)
        uow = SQLAlchemyUnitOfWork(session, outbox)

        async with uow:
            register_event_from_aggregate(event)
            await uow.commit()

    # Step 2: Verify event is in Outbox with NEW status
    async with session_factory() as session:
        stmt = select(OutboxRecord).where(
            OutboxRecord.tenant_id == "test-tenant", OutboxRecord.status == "NEW"
        )
        result = await session.execute(stmt)
        records = result.scalars().all()
        assert len(records) == 1
        assert records[0].type == "OrderCreatedEvent"

    # Step 3: Projector picks up and publishes event
    mock_bus = MockMessageBus()
    projector = OutboxProjector(
        session_factory=session_factory,
        message_bus=mock_bus,
        tenant_id="test-tenant",
        batch_size=10,
    )

    await projector.publish_all()

    # Step 4: Verify event was published
    assert len(mock_bus.published_events) == 1
    published_event = mock_bus.published_events[0]
    assert isinstance(published_event, OrderCreatedEvent)
    assert published_event.event_id == event.event_id
    assert published_event.order_id == "order-999"

    # Step 5: Verify event is marked as SENT in Outbox
    async with session_factory() as session:
        stmt = select(OutboxRecord).where(OutboxRecord.tenant_id == "test-tenant")
        result = await session.execute(stmt)
        record = result.scalar_one()
        assert record.status == "SENT"


# ==================== Run Tests ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
