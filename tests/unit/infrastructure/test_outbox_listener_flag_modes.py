from dataclasses import dataclass

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from bento.domain.domain_event import DomainEvent
from bento.persistence.sqlalchemy.base import Base
from bento.persistence.sqlalchemy.outbox_sql import OutboxRecord, SqlAlchemyOutbox
from bento.persistence.uow import SQLAlchemyUnitOfWork


@dataclass(frozen=True)
class FlagEvt(DomainEvent):
    kind: str = "flag"


@pytest.mark.asyncio
async def test_manual_persistence_when_flag_off(monkeypatch):
    monkeypatch.delenv("BENTO_OUTBOX_LISTENER", raising=False)

    engine: AsyncEngine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            outbox = SqlAlchemyOutbox(session)
            uow = SQLAlchemyUnitOfWork(session, outbox)

            agg = type("Agg", (), {"events": [FlagEvt()], "clear_events": lambda self=None: None})()

            await uow.begin()
            uow.track(agg)
            await uow.commit()

            rows = (await session.execute(OutboxRecord.__table__.select())).fetchall()
            assert len(rows) == 1
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_listener_persistence_when_flag_on(monkeypatch):
    monkeypatch.setenv("BENTO_OUTBOX_LISTENER", "1")

    engine: AsyncEngine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            outbox = SqlAlchemyOutbox(session)
            uow = SQLAlchemyUnitOfWork(session, outbox)

            agg = type("Agg", (), {"events": [FlagEvt()], "clear_events": lambda self=None: None})()

            await uow.begin()
            uow.track(agg)
            await uow.commit()

            rows = (await session.execute(OutboxRecord.__table__.select())).fetchall()
            assert len(rows) == 1
    finally:
        await engine.dispose()
