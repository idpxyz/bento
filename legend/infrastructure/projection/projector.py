# ─────────────────────────  projector.py  ──────────────────────────
"""Outbox Projector – multi‑tenant shard, Pulsar‑ready.
领域/应用出向接口 —— AbstractEventBus，UoW 与 Projector 只依赖它。
Usage example (e.g. FastAPI startup or standalone service)::

    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from infrastructure.messaging.pulsar_bus import PulsarEventBus
    from infrastructure.projection.projector import OutboxProjector

    engine = create_async_engine(POSTGRES_DSN, pool_pre_ping=True)
    sf = async_sessionmaker(engine, expire_on_commit=False)

    bus = PulsarEventBus(pulsar_client, topic_template="tenant-{tenant}")
    projector = OutboxProjector(sf, bus, tenant_id="t1")
    asyncio.create_task(projector.run_forever())

```
Design highlights
-----------------
* **Row‑level locking** (`FOR UPDATE SKIP LOCKED`) so multiple workers can
  safely pull from the same table.
* **Exactly‑once** semantics delegated to the injected `EventBus` (e.g. Pulsar
  Transaction producer).  Projector ensures *at‑least‑once* DB state → Bus.
* **Adaptive back‑off** – sleeps short when backlog exists, longer when idle.
* **Prometheus hooks** (optional) – expose counters via `prom_client` if
  available.

  rojector 作用

充当 Secondary Adapter：从 Outbox 表 轮询 status='NEW' 行

调用 EventBus Port 将事件推送到外部系统（Pulsar/Kafka/Webhook …）

投递成功 ⇒ 将行标记 SENT；失败重试 ≤ MAX_RETRY，否则 ERR

支持多租户分片（按 tenant_id 参数启动多个实例）
"""


from __future__ import annotations

import asyncio
import logging
import os
import traceback
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from idp.framework.domain.base.event import DomainEvent
from idp.framework.infrastructure.messaging.core.event_bus import AbstractEventBus
from idp.framework.infrastructure.persistence.sqlalchemy.po.outbox import OutboxPO

# Get logger with full namespace
logger = logging.getLogger("idp.framework.infrastructure.projection.projector")

# Only configure if the logger doesn't have handlers
if not logger.handlers:
    logger.setLevel(logging.INFO)

    # Ensure logs directory exists
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)

    # Prevent propagation to root logger to avoid duplicate logs
    logger.propagate = False

    # Create formatters
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Create and configure console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Create and configure file handler
    file_handler = logging.FileHandler(log_dir / 'projector.log')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

# ------------------------------ helpers -----------------------------

TRY_BATCH = 200
SLEEP_BUSY = 0.1    # backlog present
SLEEP_IDLE = 1.0    # queue empty
MAX_RETRY = 5

# ------------------------------ projector --------------------------


class OutboxProjector:
    """Continuously polls tenant‑scoped outbox rows & forwards to EventBus."""

    def __init__(
        self,
        sf: async_sessionmaker[AsyncSession],
        bus: AbstractEventBus,
        *,
        tenant_id: str,
        batch_size: int = TRY_BATCH,
    ) -> None:
        self._sf = sf
        self._bus = bus
        self._tenant = tenant_id
        self._batch = batch_size
        self._stopped = asyncio.Event()
        logger.info(
            f"Initialized OutboxProjector for tenant {tenant_id} with batch size {batch_size}")

    # -----------------------------------------------------------------
    async def run_forever(self):
        """Main loop (never exits unless cancelled)."""
        logger.info("Projector for tenant %s started", self._tenant)
        consecutive_empty_polls = 0
        while not self._stopped.is_set():
            try:
                has_more = await self._process_once()
                if has_more:
                    consecutive_empty_polls = 0
                    logger.debug(
                        f"Processed batch for tenant {self._tenant}, more items pending")
                else:
                    consecutive_empty_polls += 1
                    logger.debug(
                        f"No more items to process for tenant {self._tenant}")
            except asyncio.CancelledError:
                logger.info(f"Projector for tenant {self._tenant} cancelled")
                break
            except Exception as exc:
                logger.error("Projector loop error: %s\n%s",
                             exc, traceback.format_exc())
                await asyncio.sleep(2)
                continue

            # 自适应休眠策略
            if has_more:
                # 有事件时快速轮询
                await asyncio.sleep(0.1)
            else:
                # 无事件时使用指数退避
                sleep_time = min(
                    0.1 * (2 ** min(consecutive_empty_polls, 5)), 5.0)
                await asyncio.sleep(sleep_time)

        logger.info("Projector %s stopped", self._tenant)

    async def stop(self):
        logger.info(f"Stopping projector for tenant {self._tenant}")
        self._stopped.set()

    # -----------------------------------------------------------------
    async def _process_once(self) -> bool:
        """Fetch <=batch_size NEW rows, publish, mark SENT/ERR."""
        async with self._sf() as s, s.begin():
            stmt = (
                select(OutboxPO)
                .where(
                    OutboxPO.tenant_id == self._tenant,
                    OutboxPO.status == "NEW",
                )
                .order_by(OutboxPO.created_at)
                .limit(self._batch)
                .with_for_update(skip_locked=True)
            )
            result = await s.execute(stmt)
            rows = result.scalars().all()

            if not rows:
                return False

            logger.info(
                f"Processing {len(rows)} events for tenant {self._tenant}")

            events: list[DomainEvent] = [
                DomainEvent.model_validate(row.payload) for row in rows]

            try:
                await self._bus.publish(events)
                logger.info(
                    f"Successfully published {len(events)} events for tenant {self._tenant}")
            except Exception as exc:
                logger.warning(
                    f"Publish failed for tenant {self._tenant}, will retry later: {exc}")
                for row in rows:
                    row.retry_cnt = row.retry_cnt + \
                        1 if hasattr(row, "retry_cnt") else 1
                    if row.retry_cnt >= MAX_RETRY:
                        row.status = "ERR"
                        logger.error(
                            f"Event {row.id} for tenant {self._tenant} exceeded max retries, marked as ERR")
                return True
            else:
                # mark sent
                for row in rows:
                    row.status = "SENT"
                logger.info(
                    f"Marked {len(rows)} events as SENT for tenant {self._tenant} with ids: {', '.join([str(row.id) for row in rows])}")
                return len(rows) == self._batch

# ───────────────────────────── End of file ─────────────────────────────
