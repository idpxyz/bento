import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from bento.infrastructure.database.config import DatabaseConfig
from bento.infrastructure.database.session import (
    create_async_engine_from_config,
    create_async_session_factory,
    create_engine_and_session_factory,
)


@pytest.mark.asyncio
async def test_create_engine_and_session_factory_sqlite_memory():
    config = DatabaseConfig(url="sqlite+aiosqlite:///:memory:")

    engine, factory = create_engine_and_session_factory(config)
    assert isinstance(engine, AsyncEngine)

    async with factory() as session:
        assert isinstance(session, AsyncSession)
        # simple connectivity check
        res = await session.execute(text("SELECT 1"))
        assert res.scalar_one() == 1

    # Also test direct creation paths
    engine2 = create_async_engine_from_config(config)
    factory2 = create_async_session_factory(engine2)
    async with factory2() as session2:
        res2 = await session2.execute(text("SELECT 2"))
        assert res2.scalar_one() == 2

    await engine.dispose()
    await engine2.dispose()
