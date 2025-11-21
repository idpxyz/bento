"""Unit tests for AggregateQueryMixin (P1).

Tests aggregate query operations:
- sum_field_po
- avg_field_po
- min_field_po
- max_field_po
- count_field_po
"""

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import Integer, String

from bento.persistence.repository.sqlalchemy.base import BaseRepository


class TestBase(DeclarativeBase):
    pass


class OrderPO(TestBase):
    __tablename__ = "t_order"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    customer_id: Mapped[str] = mapped_column(String, nullable=False)
    total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


@pytest.fixture
async def setup_db():
    """Setup test database and repository."""
    engine: AsyncEngine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    try:
        async with engine.begin() as conn:
            await conn.run_sync(TestBase.metadata.create_all)

        async with async_session() as session:
            repo = BaseRepository[OrderPO, str](
                session=session,
                po_type=OrderPO,
                actor="tester",
                interceptor_chain=None,
            )

            # Create test data
            orders = [
                OrderPO(id="o1", customer_id="c1", total=100, quantity=2),
                OrderPO(id="o2", customer_id="c1", total=200, quantity=3),
                OrderPO(id="o3", customer_id="c2", total=150, quantity=1),
                OrderPO(id="o4", customer_id="c2", total=250, quantity=4),
                OrderPO(id="o5", customer_id="c3", total=300, quantity=5),
            ]
            for o in orders:
                await repo.create_po(o)

            yield repo, session

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_sum_field_po(setup_db):
    """Test summing field values."""
    repo, _ = await setup_db.__anext__()

    total_sum = await repo.sum_field_po("total")

    assert total_sum == 1000  # 100 + 200 + 150 + 250 + 300


@pytest.mark.asyncio
async def test_sum_field_po_quantity(setup_db):
    """Test summing different field."""
    repo, _ = await setup_db.__anext__()

    quantity_sum = await repo.sum_field_po("quantity")

    assert quantity_sum == 15  # 2 + 3 + 1 + 4 + 5


@pytest.mark.asyncio
async def test_avg_field_po(setup_db):
    """Test averaging field values."""
    repo, _ = await setup_db.__anext__()

    avg_total = await repo.avg_field_po("total")

    assert avg_total == 200.0  # 1000 / 5


@pytest.mark.asyncio
async def test_min_field_po(setup_db):
    """Test finding minimum field value."""
    repo, _ = await setup_db.__anext__()

    min_total = await repo.min_field_po("total")

    assert min_total == 100


@pytest.mark.asyncio
async def test_max_field_po(setup_db):
    """Test finding maximum field value."""
    repo, _ = await setup_db.__anext__()

    max_total = await repo.max_field_po("total")

    assert max_total == 300


@pytest.mark.asyncio
async def test_count_field_po_all(setup_db):
    """Test counting all field values."""
    repo, _ = await setup_db.__anext__()

    count = await repo.count_field_po("customer_id")

    assert count == 5


@pytest.mark.asyncio
async def test_count_field_po_distinct(setup_db):
    """Test counting distinct field values."""
    repo, _ = await setup_db.__anext__()

    count = await repo.count_field_po("customer_id", distinct=True)

    assert count == 3  # c1, c2, c3


@pytest.mark.asyncio
async def test_aggregate_with_empty_table():
    """Test aggregate operations on empty table."""
    engine: AsyncEngine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    try:
        async with engine.begin() as conn:
            await conn.run_sync(TestBase.metadata.create_all)

        async with async_session() as session:
            repo = BaseRepository[OrderPO, str](
                session=session,
                po_type=OrderPO,
                actor="tester",
                interceptor_chain=None,
            )

            total_sum = await repo.sum_field_po("total")
            avg_total = await repo.avg_field_po("total")
            count = await repo.count_field_po("total")

            assert total_sum == 0
            assert avg_total == 0
            assert count == 0

    finally:
        await engine.dispose()
