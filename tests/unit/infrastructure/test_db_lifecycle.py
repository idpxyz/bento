import pytest
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import String

from bento.infrastructure.database import (
    drop_all_tables,
    get_database_info,
    health_check,
    init_database,
)


class TestBase(DeclarativeBase):
    pass


class Foo(TestBase):
    __tablename__ = "t_foo"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, default="n")


@pytest.mark.asyncio
async def test_db_lifecycle_init_health_info_drop():
    engine: AsyncEngine = create_async_engine("sqlite+aiosqlite:///:memory:")

    try:
        # init (create tables)
        await init_database(engine, TestBase, check_tables=True)

        async with engine.begin() as conn:
            tables = await conn.run_sync(lambda c: inspect(c).get_table_names())
        assert "t_foo" in tables

        # health
        assert await health_check(engine) is True

        # info
        info = await get_database_info(engine)
        assert info["database_type"] == "sqlite"
        assert info["url"].startswith("sqlite+")

        # drop
        await drop_all_tables(engine, TestBase)
        async with engine.begin() as conn:
            tables_after = await conn.run_sync(lambda c: inspect(c).get_table_names())
        assert "t_foo" not in tables_after
    finally:
        await engine.dispose()
