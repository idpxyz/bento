"""Unit tests for SortingLimitingMixin (P1).

Tests sorting and limiting operations:
- find_first_po
- find_last_po
- find_top_n_po
- find_paginated_po
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


class ProductPO(TestBase):
    __tablename__ = "t_product"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


@pytest.fixture
async def setup_db():
    """Setup test database and repository."""
    engine: AsyncEngine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    try:
        async with engine.begin() as conn:
            await conn.run_sync(TestBase.metadata.create_all)

        async with async_session() as session:
            repo = BaseRepository[ProductPO, str](
                session=session,
                po_type=ProductPO,
                actor="tester",
                interceptor_chain=None,
            )

            # Create test data with different prices
            products = [
                ProductPO(id="p1", name="Product A", price=100),
                ProductPO(id="p2", name="Product B", price=500),
                ProductPO(id="p3", name="Product C", price=300),
                ProductPO(id="p4", name="Product D", price=200),
                ProductPO(id="p5", name="Product E", price=400),
            ]
            for p in products:
                await repo.create_po(p)

            yield repo, session

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_find_first_po_default_order(setup_db):
    """Test finding first entity without explicit ordering."""
    repo, _ = await setup_db.__anext__()

    first = await repo.find_first_po()

    assert first is not None
    # Without order_by, returns any first entity


@pytest.mark.asyncio
async def test_find_first_po_ascending(setup_db):
    """Test finding first entity with ascending order."""
    repo, _ = await setup_db.__anext__()

    first = await repo.find_first_po(order_by="price")

    assert first is not None
    assert first.price == 100  # Minimum price


@pytest.mark.asyncio
async def test_find_first_po_descending(setup_db):
    """Test finding first entity with descending order."""
    repo, _ = await setup_db.__anext__()

    first = await repo.find_first_po(order_by="-price")

    assert first is not None
    assert first.price == 500  # Maximum price


@pytest.mark.asyncio
async def test_find_last_po_default(setup_db):
    """Test finding last entity (default created_at order)."""
    repo, _ = await setup_db.__anext__()

    last = await repo.find_last_po()

    assert last is not None


@pytest.mark.asyncio
async def test_find_last_po_by_price(setup_db):
    """Test finding last entity ordered by price."""
    repo, _ = await setup_db.__anext__()

    last = await repo.find_last_po(order_by="price")

    assert last is not None
    assert last.price == 500  # Maximum when ordered by price


@pytest.mark.asyncio
async def test_find_top_n_po(setup_db):
    """Test finding top N entities."""
    repo, _ = await setup_db.__anext__()

    top_3 = await repo.find_top_n_po(3, order_by="price")

    assert len(top_3) == 3
    prices = [p.price for p in top_3]
    assert prices == [100, 200, 300]  # Ascending order


@pytest.mark.asyncio
async def test_find_top_n_po_descending(setup_db):
    """Test finding top N entities in descending order."""
    repo, _ = await setup_db.__anext__()

    top_3 = await repo.find_top_n_po(3, order_by="-price")

    assert len(top_3) == 3
    prices = [p.price for p in top_3]
    assert prices == [500, 400, 300]  # Descending order


@pytest.mark.asyncio
async def test_find_top_n_po_more_than_available(setup_db):
    """Test finding top N when N > total entities."""
    repo, _ = await setup_db.__anext__()

    top_10 = await repo.find_top_n_po(10, order_by="price")

    assert len(top_10) == 5  # Only 5 entities available


@pytest.mark.asyncio
async def test_find_paginated_po_first_page(setup_db):
    """Test paginated query - first page."""
    repo, _ = await setup_db.__anext__()

    products, total = await repo.find_paginated_po(page=1, page_size=2, order_by="price")

    assert len(products) == 2
    assert total == 5
    prices = [p.price for p in products]
    assert prices == [100, 200]


@pytest.mark.asyncio
async def test_find_paginated_po_second_page(setup_db):
    """Test paginated query - second page."""
    repo, _ = await setup_db.__anext__()

    products, total = await repo.find_paginated_po(page=2, page_size=2, order_by="price")

    assert len(products) == 2
    assert total == 5
    prices = [p.price for p in products]
    assert prices == [300, 400]


@pytest.mark.asyncio
async def test_find_paginated_po_last_page_partial(setup_db):
    """Test paginated query - last page with partial results."""
    repo, _ = await setup_db.__anext__()

    products, total = await repo.find_paginated_po(page=3, page_size=2, order_by="price")

    assert len(products) == 1  # Only 1 remaining
    assert total == 5
    assert products[0].price == 500


@pytest.mark.asyncio
async def test_find_paginated_po_beyond_last_page(setup_db):
    """Test paginated query - beyond last page."""
    repo, _ = await setup_db.__anext__()

    products, total = await repo.find_paginated_po(page=10, page_size=2, order_by="price")

    assert len(products) == 0
    assert total == 5
