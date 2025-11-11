"""Order read model for CQRS query optimization.

Read models are denormalized, optimized for queries, and kept in sync
with the write model through domain events or database triggers.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from bento.persistence import Base


class OrderReadModel(Base):
    """Order read model - optimized for queries.

    This is a denormalized view optimized for read operations.
    It includes pre-calculated fields like total_amount for efficient filtering.

    Synchronization strategies:
    1. Event-driven: Subscribe to OrderCreated, OrderPaid events
    2. Database triggers: Automatically sync from OrderModel
    3. Scheduled sync: Background job to rebuild read models

    Key differences from write model:
    - Includes computed fields (total_amount, items_count)
    - Denormalized data for query performance
    - No relationships, all data is flattened
    - Read-only, never modified directly by application
    """

    __tablename__ = "order_read_models"

    # Primary key
    id: Mapped[str] = mapped_column(String, primary_key=True)

    # Denormalized order data
    customer_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String, nullable=False, index=True)

    # Pre-calculated fields for query optimization
    total_amount: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        index=True,
        comment="Pre-calculated total amount for efficient filtering",
    )
    items_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="Number of items in the order"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Composite indexes for common queries
    __table_args__ = (
        Index("idx_customer_status", "customer_id", "status"),
        Index("idx_status_amount", "status", "total_amount"),
        Index("idx_created_amount", "created_at", "total_amount"),
    )


class OrderItemReadModel(Base):
    """Order item read model - denormalized for queries.

    Stores order items in a flattened structure for efficient querying.
    """

    __tablename__ = "order_item_read_models"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    order_id: Mapped[str] = mapped_column(String, nullable=False, index=True)

    # Denormalized item data
    product_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    product_name: Mapped[str] = mapped_column(String, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    subtotal: Mapped[float] = mapped_column(
        Float, nullable=False, comment="Pre-calculated: quantity * unit_price"
    )

    # Denormalized order info for join-free queries
    customer_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    order_status: Mapped[str] = mapped_column(String, nullable=False)
    order_created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        Index("idx_order_product", "order_id", "product_id"),
        Index("idx_customer_product", "customer_id", "product_id"),
    )
