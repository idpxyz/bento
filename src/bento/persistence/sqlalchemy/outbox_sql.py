from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, TIMESTAMP, Index, Integer, String, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from bento.domain.domain_event import DomainEvent
from bento.messaging.outbox import Outbox

from .base import Base


class OutboxRecord(Base):
    """ORM model for the **outbox** table.

    Stores domain events for reliable delivery with full metadata.
    """

    __tablename__: str = "outbox"

    # primary key is also the event_id (uuid4)
    # Use String for SQLite compatibility, UUID for PostgreSQL
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # multi-tenant shard key
    tenant_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True, default="default"
    )

    # optional linkage back to aggregate
    aggregate_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # event metadata
    type: Mapped[str] = mapped_column(String(128), nullable=False)
    schema_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    schema_ver: Mapped[int] = mapped_column(Integer, default=1)

    # JSON payload == DomainEvent serialized data
    # Use JSON instead of JSONB for SQLite compatibility
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    # delivery state management
    status: Mapped[str] = mapped_column(String(10), default="NEW", index=True)  # NEW | SENT | ERR
    retry_cnt: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )

    # (tenant_id, status) 复合索引
    __table_args__ = (
        Index("ix_tenant_id_status", "tenant_id", "status"),
        {"extend_existing": True},
    )

    @staticmethod
    def from_domain_event(evt: DomainEvent) -> OutboxRecord:
        """Create OutboxRecord from DomainEvent."""
        # Get event_id if available
        event_id = getattr(evt, "event_id", None) or uuid4()

        # Get tenant_id if available
        tenant_id = getattr(evt, "tenant_id", None) or "default"

        # Get aggregate_id if available
        aggregate_id = getattr(evt, "aggregate_id", None)
        if aggregate_id:
            aggregate_id = str(aggregate_id)

        # Get schema info if available
        schema_id = getattr(evt, "schema_id", None)
        schema_ver = getattr(evt, "schema_version", 1)

        # Serialize payload
        if hasattr(evt, "to_payload"):
            payload = evt.to_payload()
        else:
            from dataclasses import asdict, is_dataclass

            if is_dataclass(evt):
                payload = asdict(evt)
            else:
                payload = {k: v for k, v in evt.__dict__.items() if not k.startswith("_")}

        # Convert non-JSON-serializable types (UUID, datetime, etc.) to strings
        payload = OutboxRecord._serialize_payload(payload)

        return OutboxRecord(
            id=event_id
            if isinstance(event_id, str)
            else str(event_id)
            if event_id
            else str(uuid4()),
            tenant_id=tenant_id,
            aggregate_id=aggregate_id,
            type=evt.__class__.__name__,
            schema_id=schema_id,
            schema_ver=schema_ver,
            payload=payload,
            status="NEW",
            retry_cnt=0,
        )

    @staticmethod
    def _serialize_payload(payload: dict[str, Any]) -> dict[str, Any]:
        """Recursively convert non-JSON-serializable types to JSON-compatible formats."""
        from datetime import date, datetime, time
        from decimal import Decimal
        from uuid import UUID

        result = {}
        for key, value in payload.items():
            if isinstance(value, UUID):
                result[key] = str(value)
            elif isinstance(value, (datetime, date, time)):
                result[key] = value.isoformat()
            elif isinstance(value, Decimal):
                result[key] = float(value)
            elif isinstance(value, dict):
                result[key] = OutboxRecord._serialize_payload(value)
            elif isinstance(value, (list, tuple)):
                result[key] = [
                    OutboxRecord._serialize_payload(item)
                    if isinstance(item, dict)
                    else str(item)
                    if isinstance(item, (UUID, datetime, date, time))
                    else float(item)
                    if isinstance(item, Decimal)
                    else item
                    for item in value
                ]
            else:
                result[key] = value
        return result


class SqlAlchemyOutbox(Outbox):
    """SQLAlchemy implementation of Outbox pattern.

    Note: In the Legend architecture, this class is rarely used directly.
    Events are written to Outbox via the SQLAlchemy Event Listener.
    This class is mainly for compatibility and manual operations.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, topic: str, payload: dict) -> None:
        """Add event to outbox (legacy interface for compatibility)."""
        rec = OutboxRecord(
            type=topic,
            payload=payload,
            status="NEW",
        )
        self.session.add(rec)

    async def pull_batch(self, limit: int = 100, tenant_id: str = "default") -> Iterable[dict]:
        """Pull batch of pending events for processing."""
        q = (
            select(OutboxRecord)
            .where(OutboxRecord.tenant_id == tenant_id, OutboxRecord.status == "NEW")
            .order_by(OutboxRecord.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        rows = (await self.session.execute(q)).scalars().all()
        result = []
        for r in rows:
            result.append(
                {
                    "id": str(r.id),
                    "type": r.type,
                    "tenant_id": r.tenant_id,
                    "aggregate_id": r.aggregate_id,
                    "payload": r.payload,
                    "retry_cnt": r.retry_cnt,
                }
            )
            r.status = "PUBLISHING"
        return result

    async def mark_published(self, id: str) -> None:
        """Mark event as successfully published."""
        q = select(OutboxRecord).where(OutboxRecord.id == UUID(id))
        r = (await self.session.execute(q)).scalar_one_or_none()
        if r:
            r.status = "SENT"

    async def mark_failed(self, id: str) -> None:
        """Mark event as failed after max retries."""
        q = select(OutboxRecord).where(OutboxRecord.id == UUID(id))
        r = (await self.session.execute(q)).scalar_one_or_none()
        if r:
            r.retry_cnt += 1
            if r.retry_cnt >= 5:  # MAX_RETRY
                r.status = "ERR"
            else:
                r.status = "NEW"  # Retry
