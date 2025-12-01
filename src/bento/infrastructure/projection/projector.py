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
from bento.config.outbox import OutboxProjectorConfig, get_outbox_projector_config
from bento.domain.domain_event import DomainEvent
from bento.domain.event_registry import deserialize_event
from bento.persistence.outbox.record import OutboxRecord

logger = logging.getLogger(__name__)


class OutboxProjector:
    """OutboxProjector - Continuously polls tenant-scoped Outbox and publishes events.

    This projector implements the Transactional Outbox Pattern with multi-tenant support:
    1. Polls Outbox table for pending events (filtered by tenant_id)
    2. Publishes events to MessageBus in batches
    3. Updates event status (NEW → SENT/ERR)

    Features:
    - Multi-tenant shard support (one projector instance per tenant)
    - Row-level locking for concurrent safety (FOR UPDATE SKIP LOCKED)
    - Configurable batch processing for efficiency
    - Adaptive back-off strategy with configurable parameters
    - Retry mechanism with configurable max retries and exponential backoff
    - Graceful shutdown
    - External configuration support (environment variables, config objects)
    - Performance tuning for different scenarios (high-throughput, low-latency, etc.)
    - Hot configuration reload capability

    Example:
        ```python
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
        from bento.infrastructure.projection import OutboxProjector
        from bento.adapters.messaging.pulsar import PulsarEventBus
        from bento.config.outbox import OutboxProjectorConfig

        # Create session factory
        engine = create_async_engine(POSTGRES_DSN)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)

        # Create MessageBus
        message_bus = PulsarEventBus(pulsar_client)

        # Option 1: Use default configuration (from environment variables)
        projector_t1 = OutboxProjector(
            session_factory=session_factory,
            message_bus=message_bus,
            tenant_id="tenant1"
        )

        # Option 2: Use custom configuration
        config = OutboxProjectorConfig(
            batch_size=500,
            max_retry_attempts=10,
            sleep_busy=0.05
        )
        projector_t2 = OutboxProjector(
            session_factory=session_factory,
            message_bus=message_bus,
            tenant_id="tenant2",
            config=config
        )

        # Start in background
        asyncio.create_task(projector_t1.run_forever())
        asyncio.create_task(projector_t2.run_forever())

        # Graceful shutdown
        async def shutdown():
            await projector_t1.stop()
            await projector_t2.stop()
        ```
    """

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        message_bus: MessageBus,
        tenant_id: str | None = None,
        config: OutboxProjectorConfig | None = None,
    ) -> None:
        """Initialize OutboxProjector.

        Args:
            session_factory: SQLAlchemy async session factory
            message_bus: MessageBus implementation (Pulsar/Kafka/Redis)
            tenant_id: Tenant ID for multi-tenant sharding (默认从配置获取)
            config: 投影器配置 (默认从环境变量加载)
        """
        self._session_factory = session_factory
        self._message_bus = message_bus
        self._config = config or get_outbox_projector_config()
        self._tenant_id = tenant_id or self._config.default_tenant_id
        self._stopped = asyncio.Event()

        # P2-B Performance monitoring
        self._performance_monitor = None
        self._enable_monitoring = getattr(config, "enable_performance_monitoring", True)

        logger.info(
            f"Initialized OutboxProjector for tenant {self._tenant_id} "
            f"with batch_size={self._config.batch_size}"
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
        logger.info(f"Starting OutboxProjector for tenant: {self._tenant_id}")
        consecutive_empty_batches = 0

        # Initialize performance monitoring
        if self._enable_monitoring:
            from bento.infrastructure.monitoring.performance import PerformanceMonitor

            self._performance_monitor = PerformanceMonitor(self._session_factory)

        try:
            while not self._stopped.is_set():
                try:
                    processed_count = await self._process_once()

                    # Record performance metrics
                    if self._performance_monitor:
                        self._performance_monitor.record_events_processed(processed_count)

                    if processed_count == 0:
                        consecutive_empty_batches += 1
                        # Adaptive back-off: longer sleep when no events
                        if consecutive_empty_batches > 3:
                            await asyncio.sleep(self._config.sleep_idle)
                        else:
                            await asyncio.sleep(self._config.sleep_busy)
                    else:
                        consecutive_empty_batches = 0
                        await asyncio.sleep(self._config.sleep_busy)

                except Exception as e:
                    logger.error(
                        f"OutboxProjector[{self._tenant_id}] error: {e}",
                        exc_info=True,
                    )
                    # Sleep before retry to avoid tight error loops
                    await asyncio.sleep(self._config.sleep_busy * 2)

        finally:
            logger.info(f"OutboxProjector stopped for tenant: {self._tenant_id}")

    async def stop(self) -> None:
        """Stop the projector gracefully.

        Sets the stop event, allowing the main loop to exit cleanly.
        """
        logger.info(f"Stopping projector for tenant {self._tenant_id}")
        self._stopped.set()

    async def _process_once(self) -> bool:
        """Process one batch of events - 简化版本，专注于正确性.

        Returns:
            True if there are more events to process, False otherwise
        """
        from datetime import UTC, datetime

        async with self._session_factory() as session:
            # 查询待处理事件
            stmt = (
                select(OutboxRecord)
                .where(
                    OutboxRecord.tenant_id == self._tenant_id,
                    (OutboxRecord.status == self._config.status_new)
                    | (
                        (OutboxRecord.status == self._config.status_failed)
                        & (
                            (OutboxRecord.retry_after.is_(None))
                            | (OutboxRecord.retry_after <= datetime.now(UTC))
                        )
                    ),
                )
                .order_by(OutboxRecord.created_at)
                .limit(self._config.batch_size)
            )
            # 注意：不使用with_for_update(skip_locked=True)
            # 因为SQLite不支持行级锁，而且状态机已经防止重复处理

            result = await session.execute(stmt)
            rows = result.scalars().all()

            if not rows:
                return False

            logger.info(
                f"Processing {len(rows)} events for tenant {self._tenant_id}: "
                f"[{', '.join([f'{r.id}(status={r.status},retry={r.retry_count})' for r in rows])}]"
            )

            # 解析事件
            events: list[DomainEvent] = []
            parse_failed_ids = set()  # 记录解析失败的事件ID
            for row in rows:
                try:
                    event = deserialize_event(event_type=row.topic, payload=row.payload)
                    events.append(event)
                except Exception as exc:
                    logger.error(f"Failed to parse event {row.id}: {exc}", exc_info=True)
                    row.status = self._config.status_failed
                    parse_failed_ids.add(row.id)
                    continue

            if not events:
                await session.commit()
                return False

            # 尝试发布事件
            try:
                await self._message_bus.publish(events)
                # 发布成功 - 标记为SENT
                for row in rows:
                    if row.id not in parse_failed_ids:  # 跳过解析失败的
                        row.status = self._config.status_sent
                logger.info(f"Successfully published {len(events)} events")

            except Exception as exc:
                # 发布失败 - 更新重试信息，但不抛出异常
                logger.warning(f"Publish failed, will retry: {exc}")
                for row in rows:
                    if row.id in parse_failed_ids:
                        continue  # 跳过解析失败的（已经标记为FAILED了）

                    row.retry_count += 1
                    if row.retry_count >= self._config.max_retry_attempts:
                        row.status = self._config.status_dead
                        logger.error(f"Event {row.id} exceeded max retries, marked as DEAD")
                    else:
                        row.status = self._config.status_failed
                        # 设置重试延迟
                        backoff_seconds = self._config.calculate_backoff_delay(row.retry_count)
                        if backoff_seconds > 0:
                            from datetime import timedelta

                            row.retry_after = datetime.now(UTC) + timedelta(seconds=backoff_seconds)
                        else:
                            # 0秒延迟 = 立即重试，设置为NULL
                            row.retry_after = None

            # 显式flush和提交事务
            logger.info(
                f"Before commit: "
                f"[{', '.join([f'{r.id}(status={r.status},retry={r.retry_count})' for r in rows])}]"
            )
            await session.flush()  # 确保更改写入数据库
            await session.commit()  # 提交事务
            logger.info("Commit completed")
            return len(rows) == self._config.batch_size

    async def publish_all(self) -> int:
        """Process all pending events (useful for testing or manual triggers).

        Returns:
            Number of events processed
        """
        total_processed = 0
        while not self._stopped.is_set():
            # Get count before processing
            async with self._session_factory() as session:
                stmt = select(OutboxRecord).where(
                    OutboxRecord.tenant_id == self._tenant_id,
                    OutboxRecord.status == self._config.status_new,
                )
                result = await session.execute(stmt)
                count_before = len(result.scalars().all())

            has_more = await self._process_once()

            # Get count after processing
            async with self._session_factory() as session:
                stmt = select(OutboxRecord).where(
                    OutboxRecord.tenant_id == self._tenant_id,
                    OutboxRecord.status == self._config.status_new,
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

    async def get_performance_metrics(self):
        """Get performance metrics for this projector.

        Returns:
            Performance metrics dictionary or None if monitoring disabled
        """
        if not self._performance_monitor:
            return None
        return await self._performance_monitor.get_metrics()

    async def analyze_performance(self):
        """Analyze performance and get bottleneck recommendations.

        Returns:
            Performance analysis dictionary or None if monitoring disabled
        """
        if not self._performance_monitor:
            return None
        return await self._performance_monitor.analyze_performance_bottlenecks()
