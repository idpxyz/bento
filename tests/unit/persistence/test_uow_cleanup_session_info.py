import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from bento.persistence.outbox.record import SqlAlchemyOutbox
from bento.persistence.po.base import Base
from bento.persistence.uow import SQLAlchemyUnitOfWork


@pytest.mark.asyncio
async def test_uow_cleanup_removes_session_info():
    engine: AsyncEngine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session() as session:
            outbox = SqlAlchemyOutbox(session)
            uow = SQLAlchemyUnitOfWork(session, outbox)

            await uow.begin()
            # Verify UoW is stored in session.info
            key = "uow"
            if hasattr(session, "sync_session"):
                assert session.sync_session.info.get(key) is uow
            else:
                assert session.info.get(key) is uow

            await uow.__aexit__(None, None, None)
            # After cleanup, the reference should be removed
            if hasattr(session, "sync_session"):
                assert session.sync_session.info.get(key) is None
            else:
                assert session.info.get(key) is None
    finally:
        await engine.dispose()
