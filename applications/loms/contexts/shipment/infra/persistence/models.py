"""
Shipment Context - Domain ORM Models.

Only domain-specific models belong here.
Infrastructure models (Idempotency, Outbox, Inbox, DLQ) are in shared/infra.
"""
from loms.shared.infra.db.base import Base, FullAuditMixin
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship


class ShipmentORM(Base, FullAuditMixin):
    """Shipment aggregate persistence model.

    Inherits from FullAuditMixin which provides:
    - created_at, updated_at (timestamps)
    - created_by, updated_by (actor tracking)
    - deleted_at, deleted_by (soft delete)
    - version (optimistic locking)
    """

    __tablename__ = "shipment"
    # Note: version_id_col is automatically configured by OptimisticLockFieldMixin

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    shipment_code: Mapped[str] = mapped_column(String(64), nullable=False)
    status_code: Mapped[str] = mapped_column(String(32), nullable=False)
    mode_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    service_level_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    shipment_type_code: Mapped[str | None] = mapped_column(String(32), nullable=True)

    legs: Mapped[list["LegORM"]] = relationship(
        "LegORM",
        back_populates="shipment",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    holds: Mapped[list["HoldORM"]] = relationship(
        "HoldORM",
        back_populates="shipment",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class LegORM(Base, FullAuditMixin):
    """Shipment leg persistence model."""

    __tablename__ = "shipment_leg"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    shipment_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("shipment.id", ondelete="CASCADE"), nullable=False
    )
    leg_index: Mapped[int] = mapped_column(Integer, nullable=False)
    origin_node_id: Mapped[str] = mapped_column(String(64), nullable=False)
    destination_node_id: Mapped[str] = mapped_column(String(64), nullable=False)
    planned_departure: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))
    planned_arrival: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))
    actual_departure: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))
    actual_arrival: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))
    carrier_code: Mapped[str | None] = mapped_column(String(64))
    mode_code: Mapped[str | None] = mapped_column(String(32))

    shipment: Mapped["ShipmentORM"] = relationship("ShipmentORM", back_populates="legs")


class HoldORM(Base, FullAuditMixin):
    """Shipment hold persistence model."""

    __tablename__ = "shipment_hold"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    shipment_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("shipment.id", ondelete="CASCADE"), nullable=False
    )
    hold_type_code: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    placed_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    released_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))
    release_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    shipment: Mapped["ShipmentORM"] = relationship(
        "ShipmentORM", back_populates="holds"
    )
