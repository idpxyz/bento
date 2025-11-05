"""Pulsar + Outbox Pattern - Complete Example.

This example demonstrates the complete event-driven flow:
1. Domain events are saved to Outbox table (transactional)
2. OutboxProjector polls the Outbox table
3. Events are published to Pulsar
4. Event handlers process the events

Architecture:
    Domain Layer
        ↓ (emit events)
    Repository (save to Outbox)
        ↓ (transaction commit)
    Database (Outbox Table)
        ↓ (poll)
    OutboxProjector
        ↓ (publish)
    Pulsar
        ↓ (consume)
    Event Handlers
"""

import asyncio
import logging
from datetime import datetime

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

from adapters.messaging.pulsar import PulsarConfig, PulsarMessageBus
from bento.core.clock import now_utc
from bento.domain.domain_event import DomainEvent
from infrastructure.projection import OutboxProjector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


# ==================== Sample Domain Events ====================


class OrderCreatedEvent(DomainEvent):
    """Sample domain event: Order was created."""

    def __init__(self, order_id: str, customer_id: str, total: float) -> None:
        super().__init__(name="order.OrderCreated", occurred_at=now_utc())
        self.order_id = order_id
        self.customer_id = customer_id
        self.total = total

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "occurred_at": self.occurred_at.isoformat(),
            "order_id": self.order_id,
            "customer_id": self.customer_id,
            "total": self.total,
        }


class PaymentProcessedEvent(DomainEvent):
    """Sample domain event: Payment was processed."""

    def __init__(self, order_id: str, amount: float, payment_method: str) -> None:
        super().__init__(name="payment.PaymentProcessed", occurred_at=now_utc())
        self.order_id = order_id
        self.amount = amount
        self.payment_method = payment_method

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "occurred_at": self.occurred_at.isoformat(),
            "order_id": self.order_id,
            "amount": self.amount,
            "payment_method": self.payment_method,
        }


# ==================== Event Handlers ====================


async def handle_order_created(event: OrderCreatedEvent) -> None:
    """Handle OrderCreated event.

    Business logic:
    - Send confirmation email
    - Update inventory
    - Trigger payment processing
    """
    logger.info(
        f"📦 Order Created: order_id={event.order_id}, "
        f"customer_id={event.customer_id}, total=${event.total}"
    )

    # Simulate business logic
    await asyncio.sleep(0.1)

    logger.info(f"✅ Order {event.order_id} - Confirmation email sent")


async def handle_payment_processed(event: PaymentProcessedEvent) -> None:
    """Handle PaymentProcessed event.

    Business logic:
    - Update order status
    - Trigger fulfillment
    """
    logger.info(
        f"💳 Payment Processed: order_id={event.order_id}, "
        f"amount=${event.amount}, method={event.payment_method}"
    )

    # Simulate business logic
    await asyncio.sleep(0.1)

    logger.info(f"✅ Order {event.order_id} - Ready for fulfillment")


# ==================== Example Setup ====================


async def setup_database() -> async_sessionmaker[AsyncSession]:
    """Setup database and create session factory.

    In a real application, this would be part of your infrastructure setup.
    """
    # Use SQLite for this example (in-memory)
    # For production, use PostgreSQL
    DATABASE_URL = "sqlite+aiosqlite:///./example.db"

    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        future=True,
    )

    # Create tables (in production, use Alembic migrations)
    # Note: OutboxRecord table should already be created
    # See: src/persistence/sqlalchemy/outbox_sql.py

    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    logger.info("✅ Database setup complete")

    return session_factory


async def setup_message_bus() -> PulsarMessageBus:
    """Setup Pulsar message bus.

    In a real application, this would be part of your infrastructure setup.
    """
    # Load configuration from environment
    config = PulsarConfig.from_env()

    # Override for local development
    config.service_url = "pulsar://localhost:6650"

    # Create message bus
    message_bus = PulsarMessageBus(
        config=config,
        source="order-service",
    )

    # Start message bus
    await message_bus.start()

    logger.info(f"✅ Pulsar message bus connected to {config.service_url}")

    return message_bus


async def setup_event_handlers(message_bus: PulsarMessageBus) -> None:
    """Register event handlers.

    In a real application, this would be done in your composition root.
    """
    # Subscribe to events
    await message_bus.subscribe(OrderCreatedEvent, handle_order_created)
    await message_bus.subscribe(PaymentProcessedEvent, handle_payment_processed)

    logger.info("✅ Event handlers registered")


async def main() -> None:
    """Main example flow."""

    logger.info("=" * 80)
    logger.info("Pulsar + Outbox Pattern Example")
    logger.info("=" * 80)

    # 1. Setup infrastructure
    logger.info("\n📋 Step 1: Setup Infrastructure")
    session_factory = await setup_database()
    message_bus = await setup_message_bus()

    # 2. Register event handlers
    logger.info("\n📋 Step 2: Register Event Handlers")
    await setup_event_handlers(message_bus)

    # 3. Create and start OutboxProjector
    logger.info("\n📋 Step 3: Start OutboxProjector")
    projector = OutboxProjector(
        session_factory=session_factory,
        message_bus=message_bus,
        batch_size=50,
    )

    # Start projector in background
    projector_task = asyncio.create_task(projector.run_forever())
    logger.info("✅ OutboxProjector started")

    # 4. Simulate domain events (normally done by your application logic)
    logger.info("\n📋 Step 4: Simulate Domain Events")

    async with session_factory() as session:
        async with session.begin():
            # In a real application, these events would be:
            # 1. Emitted by AggregateRoot
            # 2. Saved to Outbox by UnitOfWork.commit()
            #
            # For this example, we'll manually insert into Outbox

            from persistence.sqlalchemy.outbox_sql import OutboxRecord
            import json

            # Event 1: OrderCreated
            order_created = OrderCreatedEvent(
                order_id="order-001",
                customer_id="cust-123",
                total=99.99,
            )

            outbox1 = OutboxRecord(
                topic="order.OrderCreated",
                payload=json.dumps(order_created.to_dict()),
                status="pending",
            )
            session.add(outbox1)

            # Event 2: PaymentProcessed
            payment_processed = PaymentProcessedEvent(
                order_id="order-001",
                amount=99.99,
                payment_method="credit_card",
            )

            outbox2 = OutboxRecord(
                topic="payment.PaymentProcessed",
                payload=json.dumps(payment_processed.to_dict()),
                status="pending",
            )
            session.add(outbox2)

            await session.commit()

            logger.info("✅ Events saved to Outbox table")

    # 5. Wait for OutboxProjector to process events
    logger.info("\n📋 Step 5: Wait for Event Processing")
    logger.info("OutboxProjector will poll the Outbox table and publish events...")

    # Give it some time to process
    await asyncio.sleep(5)

    # 6. Graceful shutdown
    logger.info("\n📋 Step 6: Graceful Shutdown")

    # Stop projector
    await projector.stop()
    projector_task.cancel()

    try:
        await projector_task
    except asyncio.CancelledError:
        pass

    # Stop message bus
    await message_bus.stop()

    logger.info("✅ Shutdown complete")

    logger.info("\n" + "=" * 80)
    logger.info("Example Complete!")
    logger.info("=" * 80)


if __name__ == "__main__":
    """Run the example.

    Prerequisites:
    1. Pulsar running at localhost:6650
       docker run -d -p 6650:6650 -p 8080:8080 apachepulsar/pulsar:latest bin/pulsar standalone

    2. Database with Outbox table created
    """

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Example interrupted by user")

