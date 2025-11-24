from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from bento.infrastructure.database.lifecycle import (
    cleanup_database,
    drop_all_tables,
    get_database_info,
    health_check,
    init_database,
)
from bento.persistence.po.base import Base


@pytest.mark.asyncio
async def test_init_database_then_exists_and_cleanup_and_info():
    engine: AsyncEngine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        # first time -> create tables
        await init_database(engine, Base, check_tables=True)
        # second time -> tables already exist branch
        await init_database(engine, Base, check_tables=True)
        # create without checking path
        await init_database(engine, Base, check_tables=False)

        # health check true
        assert await health_check(engine) is True

        # info
        info = await get_database_info(engine)
        assert "database_type" in info and info["database_type"] == "sqlite"

        # drop all tables
        await drop_all_tables(engine, Base)

    finally:
        await cleanup_database(engine)


@pytest.mark.asyncio
async def test_health_check_failure_branch():
    class Boom:
        async def __aenter__(self):
            raise RuntimeError("no connect")

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeEngine:
        def connect(self):
            return Boom()

    fe = FakeEngine()
    assert await health_check(fe) is False
