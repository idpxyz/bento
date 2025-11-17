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
class SimpleEvent(DomainEvent):
    kind: str = "simple"


class DummyBus:
    async def publish(self, event):
        raise RuntimeError("publish failed")

    async def subscribe(self, event_type, handler):
        return None

    async def unsubscribe(self, event_type, handler):
        return None

    async def start(self):
        return None

    async def stop(self):
        return None


@pytest.mark.asyncio
async def test_uow_commit_immediate_publish_retry_error_clears_events():
    engine: AsyncEngine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            outbox = SqlAlchemyOutbox(session)
            uow = SQLAlchemyUnitOfWork(session, outbox, event_bus=DummyBus())

            agg = type(
                "Agg",
                (),
                {"events": [SimpleEvent()], "clear_events": lambda self=None: None},
            )()

            await uow.begin()
            uow.track(agg)
            # commit should not raise (RetryError is caught), and events cleared
            await uow.commit()

            rows = (await session.execute(OutboxRecord.__table__.select())).fetchall()
            assert len(rows) == 1
            assert uow.pending_events == []
    finally:
        await engine.dispose()
