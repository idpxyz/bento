from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, TIMESTAMP, Index, Integer, String, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from bento.domain.domain_event import DomainEvent
from bento.messaging.outbox import Outbox
from bento.persistence.po import Base


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
    topic: Mapped[str] = mapped_column(String(128), nullable=False)  # 与 DomainEvent.topic 一致
    occurred_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    aggregate_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    schema_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    schema_version: Mapped[int] = mapped_column(Integer, default=1)

    # JSON payload == DomainEvent serialized data
    # Use JSON instead of JSONB for SQLite compatibility
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    event_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    # 简单路由（仅用于向下兼容）
    routing_key: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # delivery state management
    status: Mapped[str] = mapped_column(String(10), default="NEW", index=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    retry_after: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )

    # 性能优化的索引配置
    __table_args__ = (
        # 原有索引
        Index("ix_tenant_id_status", "tenant_id", "status"),
        Index("ix_outbox_processing", "status", "retry_after"),
        Index("ix_outbox_topic", "topic"),
        Index("ix_outbox_aggregate", "aggregate_type", "aggregate_id"),
        # P2-B 性能优化索引
        Index("ix_outbox_cleanup", "tenant_id", "created_at"),  # 历史数据清理优化
        Index("ix_outbox_query_opt", "status", "retry_after", "tenant_id"),  # 查询性能优化
        Index("ix_outbox_tenant_created", "tenant_id", "created_at", "status"),  # 复合查询优化
        Index(
            "ix_outbox_processing_tenant", "tenant_id", "status", "retry_count"
        ),  # Projector查询优化
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

        # Get occurred_at
        occurred_at = getattr(evt, "occurred_at", None)
        if occurred_at is None:
            from datetime import UTC, datetime

            occurred_at = datetime.now(UTC)

        # Get schema info if available
        schema_id = getattr(evt, "schema_id", None)
        schema_version = getattr(evt, "schema_version", 1)

        # 获取聚合类型
        aggregate_type = evt.__class__.__name__.replace("Event", "")

        # Serialize payload (try multiple serialization methods)
        if hasattr(evt, "to_payload"):
            payload = evt.to_payload()
        elif hasattr(evt, "to_dict"):
            payload = evt.to_dict()  # type: ignore[attr-defined]
        else:
            from dataclasses import asdict, is_dataclass

            if is_dataclass(evt):
                payload = asdict(evt)
            else:
                payload = {k: v for k, v in evt.__dict__.items() if not k.startswith("_")}

        # Convert non-JSON-serializable types (UUID, datetime, etc.) to strings
        payload = OutboxRecord._serialize_payload(payload)

        # 生成简单路由键
        routing_key = OutboxRecord._generate_routing_key(evt)

        # 元数据
        metadata = {
            "producer": "bento-framework",
            "event_class": evt.__class__.__name__,
            "schema_version": schema_version,
        }
        # 合并事件自身的元数据（如果有的话）
        evt_metadata = getattr(evt, "metadata", None)
        if evt_metadata:
            metadata.update(evt_metadata)

        return OutboxRecord(
            id=event_id
            if isinstance(event_id, str)
            else str(event_id)
            if event_id
            else str(uuid4()),
            tenant_id=tenant_id,
            aggregate_id=aggregate_id,
            aggregate_type=aggregate_type,
            topic=evt.topic,  # 使用新的 topic 字段
            occurred_at=occurred_at,
            schema_id=schema_id,
            schema_version=schema_version,
            payload=payload,
            event_metadata=metadata,
            routing_key=routing_key,
            status="NEW",
            retry_count=0,
        )

    @staticmethod
    def _generate_routing_key(evt: DomainEvent) -> str:
        """自动生成路由键"""
        topic = evt.topic.lower()
        # 如果 topic 是 "product.created" 格式，返回 "product.created"
        # 如果是 "ProductCreated" 格式，转换为 "product.created"
        if "." in topic:
            return topic
        else:
            # 将 CamelCase 转换为 snake_case.action 格式
            import re

            camel_to_snake = re.sub(r"(?<!^)(?=[A-Z])", "_", topic).lower()
            return camel_to_snake

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
        from datetime import UTC, datetime

        rec = OutboxRecord(
            topic=topic,
            occurred_at=datetime.now(UTC),
            payload=payload,
            event_metadata={},
            status="NEW",
        )
        self.session.add(rec)

    async def pull_batch(self, limit: int = 100, tenant_id: str = "default") -> Iterable[dict]:
        """Pull batch of pending events for processing."""
        from datetime import UTC, datetime

        q = (
            select(OutboxRecord)
            .where(
                OutboxRecord.tenant_id == tenant_id,
                (OutboxRecord.status == "NEW")
                | (
                    (OutboxRecord.status == "FAILED")
                    & (
                        (OutboxRecord.retry_after.is_(None))
                        | (OutboxRecord.retry_after <= datetime.now(UTC))
                    )
                ),
            )
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
                    "topic": r.topic,
                    "tenant_id": r.tenant_id,
                    "aggregate_id": r.aggregate_id,
                    "aggregate_type": r.aggregate_type,
                    "payload": r.payload,
                    "metadata": r.event_metadata,
                    "routing_key": r.routing_key,
                    "retry_count": r.retry_count,
                    "occurred_at": r.occurred_at.isoformat() if r.occurred_at else None,
                }
            )
            r.status = "PUBLISHING"
        return result

    async def mark_published(self, id: str) -> None:
        """Mark event as successfully published."""

        q = select(OutboxRecord).where(OutboxRecord.id == id)
        r = (await self.session.execute(q)).scalar_one_or_none()
        if r:
            r.status = "SENT"
            # 可选：记录处理时间
            # r.processed_at = datetime.now(UTC)

    async def mark_failed(self, id: str, error_message: str | None = None) -> None:
        """Mark event as failed after max retries."""
        from datetime import UTC, datetime, timedelta

        q = select(OutboxRecord).where(OutboxRecord.id == id)
        r = (await self.session.execute(q)).scalar_one_or_none()
        if r:
            r.retry_count += 1
            r.error_message = error_message

            from bento.config.outbox import get_outbox_projector_config

            config = get_outbox_projector_config()

            if r.retry_count >= config.max_retry_attempts:
                r.status = config.status_dead
            else:
                r.status = config.status_failed
                # 使用配置的指数退避策略
                backoff_seconds = config.calculate_backoff_delay(r.retry_count)
                r.retry_after = datetime.now(UTC) + timedelta(seconds=backoff_seconds)
