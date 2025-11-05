# infrastructure/persistence/sqlalchemy/interceptor/outbox_interceptor.py
from __future__ import annotations

import logging
from typing import cast as type_cast

from sqlalchemy import event
from sqlalchemy.orm import Session

from idp.framework.infrastructure.persistence.sqlalchemy.po.outbox import OutboxPO
from idp.framework.infrastructure.persistence.sqlalchemy.uow import (
    SqlAlchemyAsyncUoW,  # or your path
)

logger = logging.getLogger(__name__)

# --------------------------------- listener ---------------------------------


@event.listens_for(Session, "after_flush")
# sync listener (even for AsyncSession)
def persist_events(session: Session, flush_ctx) -> None:
    """
    Pick up unpublished DomainEvents from the running UoW and
    insert one `OutboxPO` row per event inside the same DB transaction.
    """
    logger.debug("After flush event triggered")  # 降低日志级别，避免干扰

    # 检查是否有需要处理的实体变更
    if not (session.new or session.dirty or session.deleted):
        return

    # UoW back-reference is injected in SqlAlchemyAsyncUoW.begin()
    uow: SqlAlchemyAsyncUoW | None = type_cast(
        "SqlAlchemyAsyncUoW | None", session.info.get("uow"))
    if not uow:
        # 只在确实需要 UoW 时才记录警告
        if any(hasattr(obj, 'pull_events') for obj in (session.new | session.dirty | session.deleted)):
            logger.warning(
                "No UoW found in session, but domain events may need to be processed")
        return

    events = uow.pending_events
    if not events:
        logger.debug("No pending events found")  # 降低日志级别
        return

    logger.info("Found %d events to persist", len(events))
    for evt in events:
        logger.info("Processing event: %s (id=%s)",
                    evt.__class__.__name__, evt.event_id)
        # Check if event already exists
        existing = session.query(OutboxPO).filter(
            OutboxPO.id == evt.event_id).first()
        if existing:
            logger.warning(
                "Event %s already exists in outbox, skipping", evt.event_id)
            continue

        # ← INSERT ... VALUES status='NEW', retry_cnt=0
        session.add(OutboxPO.from_domain(evt))
        logger.info("Added event %s to outbox", evt.event_id)

    # 不在此处清空；交由 UoW.commit() 在 publish 成功后清空

# ───────────────────────────── End of file ─────────────────────────────

# 为什么同步 (def, 不是 async def)
# SQLAlchemy 的 ORM 事件（after_flush, before_commit …）只接受 同步函数。
# 即使外层是 AsyncSession，内部会在 持有连接锁 的同步上下文触发。
# 在此钩子里只需要内存操作（session.add()），不会阻塞 event loop。
