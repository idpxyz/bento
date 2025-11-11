"""Order module SQLAlchemy models.

Persistence objects for Order aggregate.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
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
    # Order-level money fields (use Numeric for precision)
    discount_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    tax_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    # Shipping address (flattened)
    shipping_address_line1: Mapped[str | None] = mapped_column(String, nullable=True)
    shipping_city: Mapped[str | None] = mapped_column(String, nullable=True)
    shipping_country: Mapped[str | None] = mapped_column(String, nullable=True)
    # Polymorphic discriminators (payment/shipment)
    payment_method: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    shipment_carrier: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    # Common payment fields (minimal, optional)
    payment_card_last4: Mapped[str | None] = mapped_column(String, nullable=True)
    payment_card_brand: Mapped[str | None] = mapped_column(String, nullable=True)
    payment_paypal_payer_id: Mapped[str | None] = mapped_column(String, nullable=True)
    # Common shipment fields (minimal, optional)
    shipment_tracking_no: Mapped[str | None] = mapped_column(String, nullable=True)
    shipment_service: Mapped[str | None] = mapped_column(String, nullable=True)

    # Relationships
    items: Mapped[list[OrderItemModel]] = relationship(
        "OrderItemModel", back_populates="order", cascade="all, delete-orphan"
    )
    discounts: Mapped[list[OrderDiscountModel]] = relationship(
        "OrderDiscountModel", back_populates="order", cascade="all, delete-orphan"
    )
    tax_lines: Mapped[list[OrderTaxLineModel]] = relationship(
        "OrderTaxLineModel", back_populates="order", cascade="all, delete-orphan"
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
    # Use Numeric for precision
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    # Polymorphic discriminator for line item kinds
    kind: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="simple",
        server_default="simple",
        index=True,
    )

    # Relationships
    order: Mapped[OrderModel] = relationship("OrderModel", back_populates="items")

    @property
    def subtotal(self) -> float:
        """Calculate item subtotal (for display only)."""
        from decimal import Decimal

        return float(Decimal(self.unit_price) * Decimal(self.quantity))


class OrderDiscountModel(Base):
    """Order discount rows."""

    __tablename__ = "order_discounts"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    order_id: Mapped[str] = mapped_column(
        String, ForeignKey("orders.id"), index=True, nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    reason: Mapped[str | None] = mapped_column(String, nullable=True)

    order: Mapped[OrderModel] = relationship("OrderModel", back_populates="discounts")


class OrderTaxLineModel(Base):
    """Order tax rows."""

    __tablename__ = "order_tax_lines"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    order_id: Mapped[str] = mapped_column(
        String, ForeignKey("orders.id"), index=True, nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    tax_type: Mapped[str | None] = mapped_column(String, nullable=True)

    order: Mapped[OrderModel] = relationship("OrderModel", back_populates="tax_lines")
