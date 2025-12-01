import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from bento.persistence.outbox.record import OutboxRecord, SqlAlchemyOutbox
from bento.persistence.po.base import Base


@pytest.mark.asyncio
async def test_outbox_add_pull_mark_publish_and_fail():
    engine: AsyncEngine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            outbox = SqlAlchemyOutbox(session)

            # add
            await outbox.add(topic="TestEvent", payload={"x": 1})
            await session.flush()

            # verify one row by querying OutboxRecord directly
            rows = (await session.execute(OutboxRecord.__table__.select())).fetchall()
            assert len(rows) == 1

            # pull
            batch = list(await outbox.pull_batch(limit=10, tenant_id="default"))
            assert len(batch) == 1
            evt = batch[0]
            assert evt["topic"] == "TestEvent"
            evt_id = evt["id"]
            # status should be set to PUBLISHING in-memory; flush to persist
            await session.flush()

            # mark published
            await outbox.mark_published(evt_id)
            await session.flush()
            rec = (
                await session.execute(
                    OutboxRecord.__table__.select().where(OutboxRecord.id == evt_id)
                )
            ).first()
            assert rec is not None and rec._mapping["status"] == "SENT"

            # add another, test fail path
            await outbox.add(topic="TestEvent2", payload={"y": 2})
            await session.flush()
            batch2 = list(await outbox.pull_batch(limit=10))
            evt2_id = batch2[0]["id"]
            # call mark_failed 5 times -> ERR
            for _ in range(5):
                await outbox.mark_failed(evt2_id)
                await session.flush()
            rec2 = (
                await session.execute(
                    OutboxRecord.__table__.select().where(OutboxRecord.id == evt2_id)
                )
            ).first()
            assert rec2 is not None
            assert rec2._mapping["retry_count"] >= 5
            assert rec2._mapping["status"] == "DEAD"
    finally:
        await engine.dispose()
