"""Order module SQLAlchemy models.

Persistence objects for Order aggregate.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bento.persistence import (
    AuditFieldsMixin,
    Base,
    OptimisticLockFieldMixin,
    SoftDeleteFieldsMixin,
)


class OrderModel(Base, AuditFieldsMixin, SoftDeleteFieldsMixin, OptimisticLockFieldMixin):
    """Order persistent model.

    Inherits:
        - AuditFieldsMixin: created_at, updated_at, created_by, updated_by
        - SoftDeleteFieldsMixin: deleted_at, deleted_by, is_deleted property
        - OptimisticLockFieldMixin: version

    Note:
        All mixin fields are automatically populated by Interceptors in the repository layer.
    """

    __tablename__ = "orders"

    # Business fields
    id: Mapped[str] = mapped_column(String, primary_key=True)
    customer_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String, nullable=False, index=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    items: Mapped[list[OrderItemModel]] = relationship(
        "OrderItemModel", back_populates="order", cascade="all, delete-orphan"
    )

    @property
    def total_amount(self) -> float:
        """Calculate total amount from items (computed property for display only)."""
        return sum(item.subtotal for item in self.items)


class OrderItemModel(Base):
    """Order item persistent model.

    Note:
        Order items are child entities and don't need audit/version fields.
        They follow the lifecycle of their parent Order.
        Deleted automatically via cascade when order is deleted.
    """

    __tablename__ = "order_items"

    # Business fields
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

    @property
    def subtotal(self) -> float:
        """Calculate item subtotal."""
        return self.unit_price * self.quantity
