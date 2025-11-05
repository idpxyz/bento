# ─────────────────  infrastructure/uow/unit_of_work.py  ──────────────────
"""Async SQL‑Alchemy Unit‑of‑Work with pending‑events buffer & Tenacity retry.

Implements all hooks expected from `AbstractUnitOfWork` – *begin / _do_commit /
rollback / _cleanup* – so there are no abstract leftovers.

• Keeps a ContextVar to let AggregateRoot register events without depending on
  Session mapping.
• Exposes `session` attr for Repositories (injected in API layer).
"""

from __future__ import annotations

import contextvars
import logging
from typing import List, Sequence

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tenacity import RetryError, retry, stop_after_attempt, wait_exponential

from idp.framework.application.uow.base import AbstractUnitOfWork
from idp.framework.domain.base.event import DomainEvent
from idp.framework.infrastructure.messaging.core.event_bus import AbstractEventBus

logger = logging.getLogger(__name__)

# ------- ContextVar so Aggregates can push events without DI hell ---------
_current_uow: contextvars.ContextVar["SqlAlchemyAsyncUoW | None"] = contextvars.ContextVar(
    "current_uow", default=None
)

# --------------------- Unit‑of‑Work implementation ------------------------


class SqlAlchemyAsyncUoW(AbstractUnitOfWork):
    """Concrete UoW for async SQLAlchemy sessions.

    UoW 负责：
      1) 创建并管理同一个 AsyncSession
      2) 批量协调多个 Repository
      3) 统一 commit/rollback
    """

    def __init__(
        self,
        sf: async_sessionmaker[AsyncSession],
        bus: AbstractEventBus,
    ) -> None:
        self._sf = sf
        self._bus = bus
        self._session: AsyncSession | None = None
        self._pending_events: List[DomainEvent] = []
        self._ctx_token: contextvars.Token | None = None
        logger.info("UoW initialized with event bus: %s",
                    bus.__class__.__name__)

    # ----------------------------- context mgr -----------------------------
    async def __aenter__(self):
        logger.info("Entering UoW context")
        await self.begin()
        return self

    async def __aexit__(self, exc_t, exc, tb):
        logger.info("Exiting UoW context. Exception: %s", exc_t)
        try:
            if exc_t:
                await self.rollback()
            else:
                await self.commit()
        finally:
            await self._cleanup()


    # --------------------------- abstract hooks ---------------------------
    async def begin(self):
        """Create new session and register self in ContextVar."""
        self._session = self._sf()
        self._session.info["uow"] = self
        self._ctx_token = _current_uow.set(self)
        logger.info("UoW session started")

    async def _do_commit(self):
        logger.info("Committing UoW session")
        await self._session.commit()

    async def rollback(self):
        if self._session is not None:
            logger.info("Rolling back UoW session")
            await self._session.rollback()

    async def _cleanup(self):
        if self._session is not None:
            await self._session.close()
        if self._ctx_token is not None:
            _current_uow.reset(self._ctx_token)
        logger.info("UoW cleanup completed")

    # ------------------------------ commit -------------------------------
    async def commit(self):
        # 1) 先提交业务数据
        await self._do_commit()
        if self._pending_events:
            logger.info("Publishing %d pending events",
                        len(self._pending_events))
            try:
                # 2) 尝试发布事件（最多 3 次指数退避）
                await self._publish_with_retry(self._pending_events)
            except RetryError as retry_error:
                # 3) 重试耗尽，将事件落地到 Outbox 表
                logger.error("Failed to publish events: %s",
                             str(retry_error), exc_info=True)
                raise
            finally:
                # 4) 无论成功或失败，清空内存缓冲
                self._pending_events.clear()
        else:
            logger.info("No pending events to publish")

    # --------------- retry wrapper (at‑least‑once) -----------------------
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5))
    async def _publish_with_retry(self, events: Sequence[DomainEvent]):
        logger.info("Publishing %d events (attempt)", len(events))
        try:
            await self._bus.publish(events)
            logger.info("Events published successfully")
        except Exception as e:
            logger.error("Failed to publish events: %s", str(e), exc_info=True)
            raise

    # ----------------------- Aggregate helper ----------------------------
    def _register_event(self, evt: DomainEvent):
        logger.info("Registering event: %s", evt.__class__.__name__)
        self._pending_events.append(evt)

    # Property so other libs (e.g., Outbox listener) can read
    @property
    def pending_events(self) -> List[DomainEvent]:
        return self._pending_events

    # Expose session for repositories / API layer
    @property
    def session(self) -> AsyncSession:
        assert self._session is not None, "UoW has no active session"
        return self._session

# -------------------- helper for AggregateRoot ---------------------------


def register_event_from_aggregate(evt: DomainEvent):
    """Called inside AggregateRoot.raise_event() to push into current UoW."""
    uow = _current_uow.get(None)
    if uow:
        logger.info("Registering event from aggregate: %s",
                    evt.__class__.__name__)
        uow._register_event(evt)
    else:
        logger.warning(
            "No active UoW found when registering event from aggregate")

# Aggregates import this function to avoid circular import:
#     from idp.infrastructure.uow.unit_of_work import register_event_from_aggregate

# ───────────────────────────── End of file ─────────────────────────────
