# infrastructure/persistence.py
import os
from datetime import datetime

from infrastructure.settings import settings
from sqlalchemy import JSON, Column, DateTime, Integer, String, Text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.future import select
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = settings.database_url
engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


class AuditEventORM(Base):
    __tablename__ = "audit_event"
    id = Column(Integer, primary_key=True, index=True)
    event_time = Column(DateTime, default=datetime.utcnow)
    actor_sub = Column(String, nullable=False)
    org_id = Column(String)
    action = Column(String, nullable=False)
    resource_id = Column(String)
    decision = Column(String)
    reason = Column(Text)
    req_id = Column(String)
    extra = Column(JSON)


class AuditRepo:
    async def insert(self, event: dict) -> None:
        async with SessionLocal() as session:
            db_event = AuditEventORM(**event)
            session.add(db_event)
            await session.commit()

    async def query(self, filters: dict) -> list[dict]:
        async with SessionLocal() as session:
            stmt = select(AuditEventORM)
            for k, v in filters.items():
                stmt = stmt.where(getattr(AuditEventORM, k) == v)
            result = await session.execute(stmt)
            rows = result.scalars().all()
            return [row.__dict__ for row in rows]
