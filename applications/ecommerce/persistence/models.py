"""SQLAlchemy models for e-commerce application.

This module contains ORM models for the e-commerce aggregates.
These models are APPLICATION-SPECIFIC and should not be in the framework core.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, declarative_base, mapped_column, relationship

# Define Base here - will be imported by composition.py
Base = declarative_base()


class OrderModel(Base):
    """Order persistent model."""

    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    customer_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Relationships
    items: Mapped[list[OrderItemModel]] = relationship(
        "OrderItemModel", back_populates="order", cascade="all, delete-orphan"
    )


class OrderItemModel(Base):
    """Order item persistent model."""

    __tablename__ = "order_items"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    order_id: Mapped[str] = mapped_column(
        String, ForeignKey("orders.id"), nullable=False, index=True
    )
    product_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    product_name: Mapped[str] = mapped_column(String, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)

    # Relationships
    order: Mapped[OrderModel] = relationship("OrderModel", back_populates="items")


class OutboxMessageModel(Base):
    """Outbox message persistent model."""

    __tablename__ = "outbox_messages"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    aggregate_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    aggregate_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    event_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
