# ─────────────────────────  outbox_po.py  ──────────────────────────
"""Outbox persistence object – stores domain events for reliable delivery.

Mapped to table **outbox**:
* One row per *DomainEvent*
* Written inside the same DB transaction as business data (via interceptor)
* Read & updated by `OutboxProjector`
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict
from uuid import UUID, uuid4

from sqlalchemy import TIMESTAMP, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from idp.framework.domain.base.event import DomainEvent
from idp.framework.infrastructure.persistence.sqlalchemy.po import BasePO


class OutboxPO(BasePO):
    """ORM model for the **outbox** table."""
    __tablename__ = "outbox"

    # primary key is also the event_id (uuid4)
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

    # multi‑tenant shard key
    tenant_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True)

    # optional linkage back to aggregate
    aggregate_id: Mapped[str | None] = mapped_column(String(128))

    # event metadata
    type: Mapped[str] = mapped_column(String(128), nullable=False)
    schema_id: Mapped[str | None] = mapped_column(String(128))
    schema_ver: Mapped[int] = mapped_column(Integer, default=1)

    # JSON payload == DomainEvent.model_dump()
    payload: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)

    # delivery state management
    status: Mapped[str] = mapped_column(
        String(10), default="NEW", index=True)  # NEW | SENT | ERR
    retry_cnt: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now())

    #  tenant_id, status) 复合索引
    __table_args__ = (
        Index('ix_tenant_id_status', 'tenant_id', 'status'),
        {'extend_existing': True}
    )

    # ------------------------------------------------------------------
    @staticmethod
    def from_domain(evt: DomainEvent) -> "OutboxPO":
        return OutboxPO(
            id=evt.event_id,
            tenant_id=evt.tenant_id or "default",
            aggregate_id=str(evt.aggregate_id) if evt.aggregate_id else None,
            type=evt.__class__.__name__,
            schema_id=evt.schema_id,
            schema_ver=evt.schema_version,
            payload=evt.to_payload(),
        )

# ───────────────────────────── End of file ─────────────────────────────
