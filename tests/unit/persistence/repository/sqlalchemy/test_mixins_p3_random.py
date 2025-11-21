"""Unit tests for RandomSamplingMixin (P3).

Tests random sampling operations:
- find_random_po
- find_random_n_po
- sample_percentage_po
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


class ItemPO(TestBase):
    __tablename__ = "t_item"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


@pytest.fixture
async def setup_db():
    """Setup test database and repository."""
    engine: AsyncEngine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    try:
        async with engine.begin() as conn:
            await conn.run_sync(TestBase.metadata.create_all)

        async with async_session() as session:
            repo = BaseRepository[ItemPO, str](
                session=session,
                po_type=ItemPO,
                actor="tester",
                interceptor_chain=None,
            )

            # Create test data
            items = [
                ItemPO(id=f"i{i}", name=f"Item {i}", value=i * 10)
                for i in range(1, 21)  # 20 items
            ]
            for item in items:
                await repo.create_po(item)

            yield repo, session

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_find_random_po(setup_db):
    """Test finding one random entity."""
    repo, _ = await setup_db.__anext__()

    random_item = await repo.find_random_po()

    assert random_item is not None
    assert random_item.name.startswith("Item ")


@pytest.mark.asyncio
async def test_find_random_po_multiple_calls(setup_db):
    """Test that multiple random calls may return different entities."""
    repo, _ = await setup_db.__anext__()

    # Get 10 random items
    random_items = []
    for _ in range(10):
        item = await repo.find_random_po()
        if item:
            random_items.append(item.id)

    # Should have some results (at least 1 due to 20 items)
    assert len(random_items) > 0


@pytest.mark.asyncio
async def test_find_random_n_po(setup_db):
    """Test finding N random entities."""
    repo, _ = await setup_db.__anext__()

    random_items = await repo.find_random_n_po(5)

    assert len(random_items) == 5
    # All should be unique
    ids = [item.id for item in random_items]
    assert len(set(ids)) == 5


@pytest.mark.asyncio
async def test_find_random_n_po_more_than_total(setup_db):
    """Test finding N random when N > total count."""
    repo, _ = await setup_db.__anext__()

    random_items = await repo.find_random_n_po(100)

    assert len(random_items) == 20  # Only 20 items exist


@pytest.mark.asyncio
async def test_find_random_n_po_zero(setup_db):
    """Test finding 0 random entities."""
    repo, _ = await setup_db.__anext__()

    random_items = await repo.find_random_n_po(0)

    assert len(random_items) == 0


@pytest.mark.asyncio
async def test_find_random_n_po_negative(setup_db):
    """Test finding negative number of random entities."""
    repo, _ = await setup_db.__anext__()

    random_items = await repo.find_random_n_po(-5)

    assert len(random_items) == 0


@pytest.mark.asyncio
async def test_sample_percentage_po(setup_db):
    """Test percentage-based sampling."""
    repo, _ = await setup_db.__anext__()

    # Sample 25% of 20 items = 5 items
    sample = await repo.sample_percentage_po(25.0)

    assert len(sample) == 5


@pytest.mark.asyncio
async def test_sample_percentage_po_with_max_count(setup_db):
    """Test percentage sampling with max count limit."""
    repo, _ = await setup_db.__anext__()

    # 50% of 20 = 10, but limit to 3
    sample = await repo.sample_percentage_po(50.0, max_count=3)

    assert len(sample) == 3


@pytest.mark.asyncio
async def test_sample_percentage_po_zero(setup_db):
    """Test percentage sampling with 0%."""
    repo, _ = await setup_db.__anext__()

    sample = await repo.sample_percentage_po(0.0)

    assert len(sample) == 0


@pytest.mark.asyncio
async def test_sample_percentage_po_over_100(setup_db):
    """Test percentage sampling with >100%."""
    repo, _ = await setup_db.__anext__()

    # Should be capped at 100%
    sample = await repo.sample_percentage_po(150.0)

    assert len(sample) == 20  # All items


@pytest.mark.asyncio
async def test_sample_percentage_po_small_percentage(setup_db):
    """Test percentage sampling with small percentage."""
    repo, _ = await setup_db.__anext__()

    # 1% of 20 = 0.2 → 0 items
    sample = await repo.sample_percentage_po(1.0)

    assert len(sample) == 0


@pytest.mark.asyncio
async def test_random_operations_on_empty_table():
    """Test random operations on empty table."""
    engine: AsyncEngine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    try:
        async with engine.begin() as conn:
            await conn.run_sync(TestBase.metadata.create_all)

        async with async_session() as session:
            repo = BaseRepository[ItemPO, str](
                session=session,
                po_type=ItemPO,
                actor="tester",
                interceptor_chain=None,
            )

            random_one = await repo.find_random_po()
            random_n = await repo.find_random_n_po(5)
            sample = await repo.sample_percentage_po(50.0)

            assert random_one is None
            assert len(random_n) == 0
            assert len(sample) == 0

    finally:
        await engine.dispose()
