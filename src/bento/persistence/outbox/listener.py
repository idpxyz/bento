# infrastructure/persistence/sqlalchemy/interceptor/outbox_interceptor.py
from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping, Sequence
from typing import Any, Protocol, cast, runtime_checkable
from uuid import UUID

from sqlalchemy import event, select
from sqlalchemy.orm import Session

from bento.persistence.config import is_outbox_listener_enabled
from bento.persistence.outbox.record import OutboxRecord
from bento.persistence.uow import SQLAlchemyUnitOfWork

logger = logging.getLogger(__name__)

# --------------------------------- listener ---------------------------------

logger.info("Outbox listener module loaded (listener currently disabled, using direct persistence)")


@runtime_checkable
class OutboxSession(Protocol):
    info: Mapping[str, Any]

    def execute(self, stmt) -> Iterable[Sequence[Any]]: ...

    def add(self, obj) -> None: ...


# NOTE: This listener is currently disabled because it causes duplicate inserts when combined
# with the manual persistence approach in SQLAlchemyUnitOfWork.commit().
# The listener works but only when there are entity changes that trigger a flush.
# For AsyncSession without entity changes, the manual approach is more reliable.
# @event.listens_for(Session, "after_flush")


def persist_events_DISABLED(session: OutboxSession, flush_ctx) -> None:
    """
    Pick up unpublished DomainEvents from the running UoW and
    insert one `OutboxRecord` row per event inside the same DB transaction.
    """
    logger.info("✓ After flush event triggered!")  # INFO level to make sure we see it

    # UoW back-reference is injected in SQLAlchemyUnitOfWork.begin()
    uow: SQLAlchemyUnitOfWork | None = cast("SQLAlchemyUnitOfWork | None", session.info.get("uow"))
    if not uow:
        logger.debug("No UoW found in session")
        return

    events = uow.pending_events
    if not events:
        logger.debug("No pending events found")
        return

    logger.debug("Found %d events to persist", len(events))

    # Batch check for existing events (performance optimization)
    event_ids = [getattr(evt, "event_id", None) for evt in events if hasattr(evt, "event_id")]
    existing_ids: set[UUID] = set()

    if event_ids:
        # Use select instead of query() for async compatibility
        stmt = select(OutboxRecord.id).where(OutboxRecord.id.in_(event_ids))
        result = session.execute(stmt)
        existing_ids = {row[0] for row in result}

    # Process each event
    for evt in events:
        event_id = getattr(evt, "event_id", None)
        logger.debug("Processing event: %s (id=%s)", evt.__class__.__name__, event_id or "N/A")

        # Check if event already exists (idempotency)
        if event_id and event_id in existing_ids:
            logger.warning("Event %s already exists in outbox, skipping", event_id)
            continue

        # ← INSERT ... VALUES status='NEW', retry_cnt=0
        try:
            session.add(OutboxRecord.from_domain_event(evt))
            logger.debug("Added event %s to outbox", event_id)
        except Exception as e:
            logger.error(
                "Failed to add event %s to outbox: %s",
                event_id,
                str(e),
                exc_info=True,
            )
            # Continue processing other events
            continue

    # 不在此处清空；交由 UoW.commit() 在 publish 成功后清空


# ───────────────────────────── End of file ─────────────────────────────

# 为什么同步 (def, 不是 async def)
# SQLAlchemy 的 ORM 事件（after_flush, before_commit …）只接受 同步函数。
# 即使外层是 AsyncSession，内部会在 持有连接锁 的同步上下文触发。
# 在此钩子里只需要内存操作（session.add()），不会阻塞 event loop。


_LISTENER_INSTALLED = False


def enable_outbox_listener() -> None:
    """Idempotently enable Outbox before_commit listener.

    Safe to call multiple times.
    """
    global _LISTENER_INSTALLED
    if _LISTENER_INSTALLED:
        return
    event.listen(Session, "before_commit", _before_commit_persist, propagate=True)
    _LISTENER_INSTALLED = True


def _before_commit_persist(session: OutboxSession) -> None:
    if not is_outbox_listener_enabled():
        return
    uow: SQLAlchemyUnitOfWork | None = cast("SQLAlchemyUnitOfWork | None", session.info.get("uow"))
    if not uow:
        return
    events = uow.pending_events
    if not events:
        return
    event_ids: list[str] = []
    for evt in events:
        try:
            eid = evt.event_id  # type: ignore[attr-defined]
        except AttributeError:
            continue
        if eid is not None:
            event_ids.append(str(eid))
    existing_ids: set[str] = set()
    if event_ids:
        stmt = select(OutboxRecord.id).where(OutboxRecord.id.in_(event_ids))
        result = session.execute(stmt)
        existing_ids = {row[0] for row in result}
    for evt in events:
        try:
            eid = evt.event_id  # type: ignore[attr-defined]
        except AttributeError:
            eid = None
        eid_str = str(eid) if eid is not None else None
        if eid_str and eid_str in existing_ids:
            continue
        session.add(OutboxRecord.from_domain_event(evt))


enable_outbox_listener()
