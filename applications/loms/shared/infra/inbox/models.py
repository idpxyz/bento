from datetime import datetime

from loms.shared.infra.db.base import Base
from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column


class InboxEvent(Base):
    __tablename__ = "inbox_events"
    tenant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    consumer_group: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
