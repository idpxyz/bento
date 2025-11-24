"""Unit tests for GroupByQueryMixin (P2).

Tests group by operations:
- group_by_field_po
- group_by_date_po
- group_by_multiple_fields_po
"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import DateTime, String

from bento.persistence.repository.sqlalchemy.base import BaseRepository


class TestBase(DeclarativeBase):
    pass


class EventPO(TestBase):
    __tablename__ = "t_event"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


@pytest.fixture
async def setup_db():
    """Setup test database and repository."""
    engine: AsyncEngine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    try:
        async with engine.begin() as conn:
            await conn.run_sync(TestBase.metadata.create_all)

        async with async_session() as session:
            repo = BaseRepository[EventPO, str](
                session=session,
                po_type=EventPO,
                actor="tester",
                interceptor_chain=None,
            )

            # Create test data with various dates
            base_date = datetime(2025, 1, 1)
            events = [
                EventPO(
                    id="e1",
                    event_type="login",
                    status="success",
                    created_at=base_date,
                ),
                EventPO(
                    id="e2",
                    event_type="login",
                    status="success",
                    created_at=base_date,
                ),
                EventPO(
                    id="e3",
                    event_type="logout",
                    status="success",
                    created_at=base_date,
                ),
                EventPO(
                    id="e4",
                    event_type="login",
                    status="failed",
                    created_at=base_date + timedelta(days=1),
                ),
                EventPO(
                    id="e5",
                    event_type="purchase",
                    status="success",
                    created_at=base_date + timedelta(days=2),
                ),
            ]
            for e in events:
                await repo.create_po(e)

            yield repo, session

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_group_by_field_po(setup_db):
    """Test grouping by single field."""
    repo, _ = await setup_db.__anext__()

    counts = await repo.group_by_field_po("event_type")

    assert counts["login"] == 3
    assert counts["logout"] == 1
    assert counts["purchase"] == 1


@pytest.mark.asyncio
async def test_group_by_field_po_status(setup_db):
    """Test grouping by status field."""
    repo, _ = await setup_db.__anext__()

    counts = await repo.group_by_field_po("status")

    assert counts["success"] == 4
    assert counts["failed"] == 1


@pytest.mark.asyncio
async def test_group_by_date_po_day(setup_db):
    """Test grouping by date (day granularity)."""
    repo, _ = await setup_db.__anext__()

    counts = await repo.group_by_date_po("created_at", "day")

    # Check that we have 3 distinct dates
    assert len(counts) == 3
    # Verify total count
    assert sum(counts.values()) == 5


@pytest.mark.asyncio
async def test_group_by_date_po_month(setup_db):
    """Test grouping by date (month granularity)."""
    repo, _ = await setup_db.__anext__()

    counts = await repo.group_by_date_po("created_at", "month")

    # All events in same month
    assert len(counts) == 1
    assert sum(counts.values()) == 5


@pytest.mark.asyncio
async def test_group_by_date_po_year(setup_db):
    """Test grouping by date (year granularity)."""
    repo, _ = await setup_db.__anext__()

    counts = await repo.group_by_date_po("created_at", "year")

    # All events in same year
    assert len(counts) == 1
    assert sum(counts.values()) == 5


@pytest.mark.asyncio
async def test_group_by_multiple_fields_po(setup_db):
    """Test grouping by multiple fields."""
    repo, _ = await setup_db.__anext__()

    counts = await repo.group_by_multiple_fields_po(["event_type", "status"])

    assert counts[("login", "success")] == 2
    assert counts[("login", "failed")] == 1
    assert counts[("logout", "success")] == 1
    assert counts[("purchase", "success")] == 1


@pytest.mark.asyncio
async def test_group_by_multiple_fields_po_empty_table():
    """Test grouping on empty table."""
    engine: AsyncEngine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    try:
        async with engine.begin() as conn:
            await conn.run_sync(TestBase.metadata.create_all)

        async with async_session() as session:
            repo = BaseRepository[EventPO, str](
                session=session,
                po_type=EventPO,
                actor="tester",
                interceptor_chain=None,
            )

            counts = await repo.group_by_field_po("event_type")

            assert len(counts) == 0

    finally:
        await engine.dispose()
