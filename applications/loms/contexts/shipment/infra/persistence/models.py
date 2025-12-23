"""
Shipment Context - Domain ORM Models.

Only domain-specific models belong here.
Infrastructure models (Idempotency, Outbox, Inbox, DLQ) are in shared/infra.
"""
from sqlalchemy import String, BigInteger, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from loms.shared.infra.db.base import Base


class ShipmentORM(Base):
    """Shipment aggregate persistence model."""
    __tablename__ = "shipment"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    shipment_code: Mapped[str] = mapped_column(String(64), nullable=False)
    status_code: Mapped[str] = mapped_column(String(32), nullable=False)
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
