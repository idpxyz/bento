"""Idempotency Record - SQLAlchemy model for command idempotency.

This module provides the IdempotencyRecord ORM model and SqlAlchemyIdempotency
implementation for the Idempotency pattern.

The idempotency table stores command results keyed by client-provided
idempotency keys for exactly-once command execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, TIMESTAMP, Index, Integer, String, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from bento.core.exceptions import DomainException
from bento.persistence.po import Base


class IdempotencyRecord(Base):
    """ORM model for the **idempotency** table.

    Stores command execution results for idempotent request handling.

    Attributes:
        idempotency_key: Client-provided unique key (primary key)
        tenant_id: Multi-tenant shard key
        operation: Name of the operation/command
        request_hash: Hash of the request for conflict detection
        response: Cached response data
        status_code: HTTP status code of the response
        created_at: When the record was created
        expires_at: When the record expires (for cleanup)
    """

    __tablename__: str = "idempotency"

    # Primary key is the idempotency_key (client-provided)
    idempotency_key: Mapped[str] = mapped_column(String(64), primary_key=True)

    # Multi-tenant shard key
    tenant_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True, default="default"
    )

    # Operation metadata
    operation: Mapped[str] = mapped_column(String(128), nullable=False)
    request_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Cached response
    response: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    status_code: Mapped[int] = mapped_column(Integer, default=200)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    # Processing state: COMPLETED or FAILED (no PENDING needed)
    # Simplified: we don't track "processing" state, just final results
    state: Mapped[str] = mapped_column(String(20), default="COMPLETED")

    # Indexes for common queries
    __table_args__ = (
        # 基础索引
        Index("ix_idempotency_tenant", "tenant_id"),
        Index("ix_idempotency_expires", "expires_at"),
        Index("ix_idempotency_tenant_op", "tenant_id", "operation"),
        # 清理优化索引
        Index("ix_idempotency_cleanup", "tenant_id", "expires_at"),
        # 状态查询索引
        Index("ix_idempotency_tenant_state", "tenant_id", "state"),
        # 幂等查询优化（最常用的查询）
        Index("ix_idempotency_lookup", "tenant_id", "idempotency_key", "state"),
        {"extend_existing": True},
    )

    @staticmethod
    def create(
        idempotency_key: str,
        operation: str,
        tenant_id: str = "default",
        request_hash: str | None = None,
        response: dict[str, Any] | None = None,
        status_code: int = 200,
        expires_at: datetime | None = None,
        state: str = "PENDING",
    ) -> IdempotencyRecord:
        """Create an IdempotencyRecord.

        Args:
            idempotency_key: Client-provided unique key
            operation: Name of the operation
            tenant_id: Tenant identifier
            request_hash: Hash of request for conflict detection
            response: Cached response data
            status_code: HTTP status code
            expires_at: When the record expires
            state: Processing state

        Returns:
            IdempotencyRecord instance
        """
        return IdempotencyRecord(
            idempotency_key=idempotency_key,
            operation=operation,
            tenant_id=tenant_id,
            request_hash=request_hash,
            response=response,
            status_code=status_code,
            expires_at=expires_at,
            state=state,
        )


@dataclass
class IdempotencyConflictException(DomainException):
    """Raised when idempotency key is reused with different request.

    Inherits from DomainException for consistent exception handling
    and automatic integration with Contract-as-Code reason codes.

    Attributes:
        idempotency_key: The conflicting idempotency key
    """

    idempotency_key: str = ""

    def __post_init__(self):
        # Set reason_code before calling parent
        if not self.reason_code:
            object.__setattr__(self, 'reason_code', "IDEMPOTENCY_CONFLICT")
        # Build message
        if not self.message:
            object.__setattr__(self, 'message', f"Idempotency conflict for key: {self.idempotency_key}")
        # Add details
        self.details.update({"idempotency_key": self.idempotency_key})
        super().__post_init__()


class SqlAlchemyIdempotency:
    """SQLAlchemy implementation of Idempotency pattern.

    Provides methods for storing and retrieving idempotent command results.

    Example:
        ```python
        idempotency = SqlAlchemyIdempotency(session)

        # In API handler
        @app.post("/orders")
        async def create_order(
            command: CreateOrderCommand,
            idempotency_key: str = Header(None, alias="Idempotency-Key"),
        ):
            if idempotency_key:
                # Check for cached response
                cached = await idempotency.get_response(idempotency_key)
                if cached:
                    return JSONResponse(
                        content=cached.response,
                        status_code=cached.status_code,
                    )

                # Lock the key (prevent concurrent processing)
                await idempotency.lock(idempotency_key, "CreateOrder")

            # Process command
            result = await handler.execute(command)

            if idempotency_key:
                # Store response
                await idempotency.store_response(
                    idempotency_key=idempotency_key,
                    response=result.to_dict(),
                    status_code=201,
                )

            return result
        ```
    """

    # Default TTL: 24 hours
    DEFAULT_TTL_SECONDS = 86400

    def __init__(self, session: AsyncSession, tenant_id: str = "default"):
        """Initialize idempotency store.

        Args:
            session: SQLAlchemy async session
            tenant_id: Default tenant ID for operations
        """
        self._session = session
        self._tenant_id = tenant_id

    async def get_response(self, idempotency_key: str) -> IdempotencyRecord | None:
        """Get cached response for an idempotency key.

        Args:
            idempotency_key: The idempotency key to look up

        Returns:
            IdempotencyRecord if found and completed, None otherwise
        """
        stmt = select(IdempotencyRecord).where(
            IdempotencyRecord.idempotency_key == idempotency_key,
            IdempotencyRecord.tenant_id == self._tenant_id,
            IdempotencyRecord.state == "COMPLETED",
        )
        result = await self._session.execute(stmt)
        record = result.scalar_one_or_none()

        # Check if expired
        if record and record.expires_at:
            from bento.core.clock import now_utc
            from datetime import timezone

            now = now_utc()
            expires = record.expires_at
            # Ensure both are timezone-aware for comparison
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if expires < now:
                return None  # Expired

        return record

    async def is_processing(self, idempotency_key: str) -> bool:
        """Check if a request is currently being processed.

        Note: Simplified implementation without PENDING state.
        Always returns False since we don't track processing state.

        Args:
            idempotency_key: The idempotency key to check

        Returns:
            Always False (no PENDING state in simplified design)
        """
        # Simplified: no PENDING state tracking
        return False

    async def lock(
        self,
        idempotency_key: str,
        operation: str,
        request_hash: str | None = None,
        ttl_seconds: int | None = None,
    ) -> IdempotencyRecord | None:
        """Check if idempotency key already exists.

        Simplified design: no locking, just check for existing record.
        If exists, returns the existing record.
        If not exists, returns None (caller should process and call store_response).

        Args:
            idempotency_key: Client-provided unique key
            operation: Name of the operation (not used in simplified design)
            request_hash: Optional hash of request for conflict detection
            ttl_seconds: Not used in simplified design

        Returns:
            Existing IdempotencyRecord if found, None otherwise

        Raises:
            IdempotencyConflictException: If key exists with different request
        """
        # Check if key already exists
        existing = await self._get_record(idempotency_key)
        if existing:
            # Check for conflict (same key, different request)
            if request_hash and existing.request_hash != request_hash:
                raise IdempotencyConflictException(
                    reason_code="IDEMPOTENCY_CONFLICT",
                    idempotency_key=idempotency_key,
                )
            # Already completed, return existing
            return existing

        # Not found, caller should process and store
        return None

    async def store_response(
        self,
        idempotency_key: str,
        response: dict[str, Any],
        status_code: int = 200,
        operation: str = "",
        request_hash: str | None = None,
        ttl_seconds: int | None = None,
    ) -> IdempotencyRecord:
        """Store the response for an idempotency key.

        Simplified design: creates a COMPLETED record directly.
        Uses merge for upsert behavior (handles concurrent inserts).

        Args:
            idempotency_key: The idempotency key
            response: Response data to cache
            status_code: HTTP status code
            operation: Name of the operation
            request_hash: Optional hash of request for conflict detection
            ttl_seconds: Time-to-live in seconds (default: 24 hours)

        Returns:
            Created IdempotencyRecord
        """
        from datetime import timedelta

        from bento.core.clock import now_utc

        # Calculate expiry
        ttl = ttl_seconds or self.DEFAULT_TTL_SECONDS
        expires_at = now_utc() + timedelta(seconds=ttl)

        # Create completed record
        record = IdempotencyRecord.create(
            idempotency_key=idempotency_key,
            operation=operation,
            tenant_id=self._tenant_id,
            request_hash=request_hash,
            response=response,
            status_code=status_code,
            state="COMPLETED",
            expires_at=expires_at,
        )

        # Use merge for upsert behavior (handles concurrent inserts gracefully)
        record = await self._session.merge(record)
        return record

    async def mark_failed(self, idempotency_key: str) -> None:
        """Mark a request as failed (allows retry).

        Args:
            idempotency_key: The idempotency key
        """
        record = await self._get_record(idempotency_key)
        if record:
            record.state = "FAILED"

    async def _get_record(self, idempotency_key: str) -> IdempotencyRecord | None:
        """Get record by idempotency key."""
        stmt = select(IdempotencyRecord).where(
            IdempotencyRecord.idempotency_key == idempotency_key,
            IdempotencyRecord.tenant_id == self._tenant_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def cleanup_expired(self) -> int:
        """Delete expired idempotency records.

        Returns:
            Number of records deleted
        """
        from sqlalchemy import delete

        from bento.core.clock import now_utc

        stmt = delete(IdempotencyRecord).where(
            IdempotencyRecord.tenant_id == self._tenant_id,
            IdempotencyRecord.expires_at < now_utc(),
        )
        cursor_result = await self._session.execute(stmt)
        # CursorResult from DELETE has rowcount
        return getattr(cursor_result, "rowcount", 0) or 0
