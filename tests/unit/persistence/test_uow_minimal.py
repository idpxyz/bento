from dataclasses import dataclass

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from bento.domain.domain_event import DomainEvent
from bento.persistence.outbox.record import OutboxRecord, SqlAlchemyOutbox
from bento.persistence.po.base import Base
from bento.persistence.uow import SQLAlchemyUnitOfWork


@dataclass(frozen=True)
class SimpleEvent(DomainEvent):
    kind: str = "simple"


class AggStub:
    def __init__(self, events: list[DomainEvent]) -> None:
        self.events = events

    def clear_events(self) -> None:
        self.events.clear()


@pytest.mark.asyncio
async def test_uow_commit_persists_outbox_and_clears_events():
    engine: AsyncEngine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            outbox = SqlAlchemyOutbox(session)
            uow = SQLAlchemyUnitOfWork(session, outbox)

            agg = AggStub([SimpleEvent()])
            await uow.begin()
            uow.track(agg)
            await uow.commit()

            # events persisted
            rows = (await session.execute(OutboxRecord.__table__.select())).fetchall()
            assert len(rows) == 1
            # cleared
            assert uow.pending_events == []
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_uow_rollback_discards_events():
    engine: AsyncEngine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            outbox = SqlAlchemyOutbox(session)
            uow = SQLAlchemyUnitOfWork(session, outbox)

            agg = AggStub([SimpleEvent()])
            await uow.begin()
            uow.track(agg)
            await uow.rollback()

            rows = (await session.execute(OutboxRecord.__table__.select())).fetchall()
            assert len(rows) == 0
    finally:
        await engine.dispose()


class DummyRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session


@pytest.mark.asyncio
async def test_uow_repository_registration_and_cache():
    engine: AsyncEngine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            outbox = SqlAlchemyOutbox(session)
            uow = SQLAlchemyUnitOfWork(session, outbox)

            class AggType:
                pass

            uow.register_repository(AggType, lambda s: DummyRepo(s))
            r1 = uow.repository(AggType)
            r2 = uow.repository(AggType)
            assert r1 is r2 and isinstance(r1, DummyRepo)

            with pytest.raises(ValueError):
                _ = uow.repository(str)  # unregistered
    finally:
        await engine.dispose()
