"""OutboxProjector - Reliable event publisher from Outbox table.

This module provides OutboxProjector, a background service that continuously
polls the Outbox table and publishes events to the message bus.

Based on Legend system's projector architecture with:
- Multi-tenant shard support
- Row-level locking (FOR UPDATE SKIP LOCKED) for concurrent safety
- Batch processing for efficiency
- Adaptive back-off strategy
- Retry mechanism with max retries
- Graceful shutdown support

Architecture:
    Database (Outbox Table)
        ↓ (poll)
    OutboxProjector
        ↓ (publish)
    MessageBus (Pulsar/Kafka/Redis)

Design highlights:
- **Row-level locking** (`FOR UPDATE SKIP LOCKED`) so multiple workers can
  safely pull from the same table.
- **Exactly-once** semantics delegated to the injected EventBus.
- **Adaptive back-off** – sleeps short when backlog exists, longer when idle.
"""

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bento.application.ports.message_bus import MessageBus
from bento.domain.domain_event import DomainEvent
from bento.domain.event_registry import deserialize_event
from bento.persistence.outbox.record import OutboxRecord

from .config import (
    DEFAULT_BATCH_SIZE,
    MAX_RETRY,
    SLEEP_BUSY,
    SLEEP_IDLE,
    SLEEP_IDLE_MAX,
    STATUS_ERR,
    STATUS_NEW,
    STATUS_SENT,
)

logger = logging.getLogger(__name__)


class OutboxProjector:
    """OutboxProjector - Continuously polls tenant-scoped Outbox and publishes events.

    This projector implements the Transactional Outbox Pattern with multi-tenant support:
    1. Polls Outbox table for pending events (filtered by tenant_id)
    2. Publishes events to MessageBus in batches
    3. Updates event status (NEW → SENT/ERR)

    Features:
    - Multi-tenant shard support (one projector instance per tenant)
    - Row-level locking for concurrent safety
    - Batch processing for efficiency
    - Adaptive back-off strategy
    - Retry mechanism with max retries
    - Graceful shutdown

    Example:
        ```python
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
        from bento.infrastructure.projection import OutboxProjector
        from bento.adapters.messaging.pulsar import PulsarEventBus

        # Create session factory
        engine = create_async_engine(POSTGRES_DSN)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)

        # Create MessageBus
        message_bus = PulsarEventBus(pulsar_client)

        # Create and start projector for each tenant
        projector_t1 = OutboxProjector(
            session_factory=session_factory,
            message_bus=message_bus,
            tenant_id="tenant1",
            batch_size=200
        )

        # Start in background
        asyncio.create_task(projector_t1.run_forever())

        # Graceful shutdown
        async def shutdown():
            await projector_t1.stop()
        ```
    """

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        message_bus: MessageBus,
        tenant_id: str = "default",
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> None:
        """Initialize OutboxProjector.

        Args:
            session_factory: SQLAlchemy async session factory
            message_bus: MessageBus implementation (Pulsar/Kafka/Redis)
            tenant_id: Tenant ID for multi-tenant sharding
            batch_size: Number of events to process per batch
        """
        self._session_factory = session_factory
        self._message_bus = message_bus
        self._tenant_id = tenant_id
        self._batch_size = batch_size
        self._stopped = asyncio.Event()

        logger.info(
            f"Initialized OutboxProjector for tenant {tenant_id} with batch_size={batch_size}"
        )

    async def run_forever(self) -> None:
        """Main loop - continuously polls and publishes events.

        This method runs until stopped or cancelled.

        The loop:
        1. Polls Outbox table for pending events (tenant-scoped)
        2. Publishes events to MessageBus in batches
        3. Updates event status
        4. Uses adaptive back-off (quick when busy, longer when idle)
        """
        logger.info(f"Projector for tenant {self._tenant_id} started")
        consecutive_empty_polls = 0

        try:
            while not self._stopped.is_set():
                try:
                    has_more = await self._process_once()

                    if has_more:
                        consecutive_empty_polls = 0
                        logger.debug(
                            f"Processed batch for tenant {self._tenant_id}, more items pending"
                        )
                    else:
                        consecutive_empty_polls += 1
                        logger.debug(f"No more items to process for tenant {self._tenant_id}")

                except asyncio.CancelledError:
                    logger.info(f"Projector for tenant {self._tenant_id} cancelled")
                    break
                except Exception as exc:
                    logger.error(
                        f"Projector loop error for tenant {self._tenant_id}: {exc}",
                        exc_info=True,
                    )
                    # Wait before retrying
                    await asyncio.sleep(2)
                    continue

                # Adaptive back-off strategy
                if has_more:
                    # Backlog exists: quick polling
                    await asyncio.sleep(SLEEP_BUSY)
                else:
                    # Queue empty: exponential back-off (capped)
                    sleep_time = min(
                        SLEEP_IDLE * (2 ** min(consecutive_empty_polls, 5)),
                        SLEEP_IDLE_MAX,
                    )
                    await asyncio.sleep(sleep_time)

        finally:
            logger.info(f"Projector {self._tenant_id} stopped")

    async def stop(self) -> None:
        """Stop the projector gracefully.

        Sets the stop event, allowing the main loop to exit cleanly.
        """
        logger.info(f"Stopping projector for tenant {self._tenant_id}")
        self._stopped.set()

    async def _process_once(self) -> bool:
        """Process one batch of events (Legend-style).

        Steps:
        1. Fetch NEW events for this tenant (with row-level lock)
        2. Parse events from payload using DomainEvent.model_validate
        3. Publish all events in batch to MessageBus
        4. Update status (SENT or increment retry_cnt/mark ERR)

        Returns:
            True if there are more events to process (batch was full),
            False otherwise
        """
        async with self._session_factory() as session, session.begin():
            # Fetch NEW events with row-level lock (tenant-scoped)
            stmt = (
                select(OutboxRecord)
                .where(
                    OutboxRecord.tenant_id == self._tenant_id,
                    OutboxRecord.status == STATUS_NEW,
                )
                .order_by(OutboxRecord.created_at)
                .limit(self._batch_size)
                .with_for_update(skip_locked=True)
            )

            result = await session.execute(stmt)
            rows = result.scalars().all()

            if not rows:
                return False

            logger.info(f"Processing {len(rows)} events for tenant {self._tenant_id}")

            # Parse events from payload using event registry
            events: list[DomainEvent] = []
            for row in rows:
                try:
                    # Deserialize using event registry
                    event = deserialize_event(event_type=row.type, payload=row.payload)
                    events.append(event)
                    logger.debug(
                        "Deserialized event %s (id=%s) for tenant %s",
                        row.type,
                        row.id,
                        self._tenant_id,
                    )
                except Exception as exc:
                    logger.error(
                        f"Failed to parse event from record {row.id}: {exc}",
                        exc_info=True,
                    )
                    # Mark as ERR immediately for parse errors
                    row.status = STATUS_ERR
                    continue

            if not events:
                # All events failed to parse
                return False

            # Publish all events in batch (Legend-style)
            try:
                await self._message_bus.publish(events)
                logger.info(
                    f"Successfully published {len(events)} events for tenant {self._tenant_id}"
                )
            except Exception as exc:
                # Publish failed - increment retry_cnt
                logger.warning(
                    f"Publish failed for tenant {self._tenant_id}, will retry later: {exc}"
                )
                for row in rows:
                    if row.status != STATUS_ERR:  # Skip already failed rows
                        row.retry_cnt = getattr(row, "retry_cnt", 0) + 1
                        if row.retry_cnt >= MAX_RETRY:
                            row.status = STATUS_ERR
                            logger.error(
                                f"Event {row.id} for tenant {self._tenant_id} "
                                f"exceeded max retries, marked as ERR"
                            )
                        # else: keep status as NEW for retry
                return True
            else:
                # Mark all successfully published events as SENT
                for row in rows:
                    if row.status != STATUS_ERR:  # Skip parse-failed rows
                        row.status = STATUS_SENT
                logger.info(
                    f"Marked {len(rows)} events as SENT for tenant {self._tenant_id} with ids: "
                    f"{', '.join([str(row.id) for row in rows])}"
                )
                return len(rows) == self._batch_size

    async def publish_all(self) -> int:
        """Process all pending events (useful for testing or manual triggers).

        Returns:
            Number of events processed
        """
        total_processed = 0
        while not self._stopped.is_set():
            # Get count before processing
            async with self._session_factory() as session:
                from bento.infrastructure.projection.config import STATUS_NEW

                stmt = select(OutboxRecord).where(
                    OutboxRecord.tenant_id == self._tenant_id,
                    OutboxRecord.status == STATUS_NEW,
                )
                result = await session.execute(stmt)
                count_before = len(result.scalars().all())

            has_more = await self._process_once()

            # Get count after processing
            async with self._session_factory() as session:
                from bento.infrastructure.projection.config import STATUS_NEW

                stmt = select(OutboxRecord).where(
                    OutboxRecord.tenant_id == self._tenant_id,
                    OutboxRecord.status == STATUS_NEW,
                )
                result = await session.execute(stmt)
                count_after = len(result.scalars().all())

            # Calculate how many were processed
            processed_this_batch = count_before - count_after
            total_processed += processed_this_batch

            if not has_more:
                break

        logger.info(f"Published {total_processed} events")
        return total_processed
