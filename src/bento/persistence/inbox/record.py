"""Inbox Record - SQLAlchemy model for message deduplication.

This module provides the InboxRecord ORM model and SqlAlchemyInbox implementation
for the Inbox pattern.

The inbox table stores processed message IDs to enable exactly-once processing.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, TIMESTAMP, Index, String, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from bento.persistence.po import Base


class InboxRecord(Base):
    """ORM model for the **inbox** table.

    Stores processed message IDs for deduplication (exactly-once processing).

    Attributes:
        message_id: Unique identifier of the processed message (primary key)
        tenant_id: Multi-tenant shard key
        event_type: Type of event that was processed
        processed_at: When the message was processed
        payload_hash: Optional hash of payload for debugging
        metadata: Additional metadata about processing
    """

    __tablename__: str = "inbox"

    # Primary key is the message_id (from incoming event)
    message_id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Multi-tenant shard key
    tenant_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True, default="default"
    )

    # Event metadata
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    source: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Processing info
    processed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )

    # Optional: store payload hash for debugging/audit
    payload_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Optional: store processing result or extra info
    extra_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Indexes for common queries
    __table_args__ = (
        # 基础索引
        Index("ix_inbox_tenant_event", "tenant_id", "event_type"),
        Index("ix_inbox_processed_at", "processed_at"),
        Index("ix_inbox_tenant_processed", "tenant_id", "processed_at"),
        # 清理优化索引
        Index("ix_inbox_cleanup", "tenant_id", "processed_at"),
        # 去重查询优化（最常用的查询）
        Index("ix_inbox_dedup", "tenant_id", "message_id"),
        {"extend_existing": True},
    )

    @staticmethod
    def create(
        message_id: str,
        event_type: str,
        tenant_id: str = "default",
        source: str | None = None,
        payload_hash: str | None = None,
        extra_data: dict[str, Any] | None = None,
    ) -> InboxRecord:
        """Create an InboxRecord.

        Args:
            message_id: Unique message identifier
            event_type: Type of event processed
            tenant_id: Tenant identifier
            source: Source service/system
            payload_hash: Optional hash of payload
            extra_data: Optional extra data

        Returns:
            InboxRecord instance
        """
        return InboxRecord(
            message_id=message_id,
            event_type=event_type,
            tenant_id=tenant_id,
            source=source,
            payload_hash=payload_hash,
            extra_data=extra_data,
        )


class SqlAlchemyInbox:
    """SQLAlchemy implementation of Inbox pattern.

    Provides methods for checking and recording processed messages
    to ensure exactly-once processing.

    Example:
        ```python
        inbox = SqlAlchemyInbox(session)

        # In message handler
        async def handle_order_created(event_id: str, payload: dict):
            # Check if already processed
            if await inbox.is_processed(event_id):
                logger.info(f"Skipping duplicate: {event_id}")
                return

            # Process the message
            await process_order(payload)

            # Mark as processed
            await inbox.mark_processed(
                message_id=event_id,
                event_type="OrderCreated",
                payload=payload,
            )
        ```
    """

    def __init__(self, session: AsyncSession, tenant_id: str = "default"):
        """Initialize inbox.

        Args:
            session: SQLAlchemy async session
            tenant_id: Default tenant ID for operations
        """
        self._session = session
        self._tenant_id = tenant_id

    async def is_processed(self, message_id: str) -> bool:
        """Check if a message has already been processed.

        Args:
            message_id: The message ID to check

        Returns:
            True if message was already processed, False otherwise
        """
        stmt = select(InboxRecord.message_id).where(
            InboxRecord.message_id == message_id,
            InboxRecord.tenant_id == self._tenant_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def mark_processed(
        self,
        message_id: str,
        event_type: str,
        payload: dict[str, Any] | None = None,
        source: str | None = None,
        extra_data: dict[str, Any] | None = None,
    ) -> InboxRecord:
        """Mark a message as processed.

        This should be called after successfully processing a message,
        within the same transaction as the business logic.

        Uses INSERT ... ON CONFLICT DO NOTHING for idempotency.
        If the message was already processed, returns the existing record.

        Args:
            message_id: Unique message identifier
            event_type: Type of event processed
            payload: Optional payload (used to compute hash)
            source: Optional source service
            extra_data: Optional additional data

        Returns:
            InboxRecord (existing or newly created)
        """
        # Check if already exists (fast path)
        existing = await self.get_record(message_id)
        if existing:
            return existing

        # Compute payload hash if payload provided
        payload_hash = None
        if payload:
            import hashlib
            import json

            payload_str = json.dumps(payload, sort_keys=True, default=str)
            payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()[:16]

        record = InboxRecord.create(
            message_id=message_id,
            event_type=event_type,
            tenant_id=self._tenant_id,
            source=source,
            payload_hash=payload_hash,
            extra_data=extra_data,
        )

        # Use merge for upsert behavior (handles concurrent inserts gracefully)
        record = await self._session.merge(record)
        return record

    async def get_record(self, message_id: str) -> InboxRecord | None:
        """Get inbox record by message ID.

        Args:
            message_id: The message ID to look up

        Returns:
            InboxRecord if found, None otherwise
        """
        stmt = select(InboxRecord).where(
            InboxRecord.message_id == message_id,
            InboxRecord.tenant_id == self._tenant_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def cleanup_old_records(self, older_than_days: int = 30) -> int:
        """Delete old inbox records for storage management.

        Args:
            older_than_days: Delete records older than this many days

        Returns:
            Number of records deleted
        """
        from datetime import timedelta

        from sqlalchemy import delete

        from bento.core.clock import now_utc

        cutoff = now_utc() - timedelta(days=older_than_days)

        stmt = delete(InboxRecord).where(
            InboxRecord.tenant_id == self._tenant_id,
            InboxRecord.processed_at < cutoff,
        )
        cursor_result = await self._session.execute(stmt)
        # CursorResult from DELETE has rowcount
        return getattr(cursor_result, "rowcount", 0) or 0
