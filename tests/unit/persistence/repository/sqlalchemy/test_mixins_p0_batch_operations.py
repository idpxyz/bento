"""Unit tests for BatchOperationsMixin (P0).

Tests batch ID operations:
- get_po_by_ids
- exists_po_by_id
- delete_po_by_ids
"""

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import String

from bento.persistence.repository.sqlalchemy.base import BaseRepository


class TestBase(DeclarativeBase):
    pass


class ProductPO(TestBase):
    __tablename__ = "t_product"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    sku: Mapped[str] = mapped_column(String, nullable=False)
    price: Mapped[int] = mapped_column(nullable=False, default=0)


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

            # Create test data
            products = [
                ProductPO(id="p1", name="Product 1", sku="SKU-001", price=100),
                ProductPO(id="p2", name="Product 2", sku="SKU-002", price=200),
                ProductPO(id="p3", name="Product 3", sku="SKU-003", price=300),
                ProductPO(id="p4", name="Product 4", sku="SKU-004", price=400),
            ]
            for p in products:
                await repo.create_po(p)

            yield repo, session

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_get_po_by_ids_success(setup_db):
    """Test batch retrieval by IDs."""
    repo, _ = await setup_db.__anext__()

    # Get multiple products
    products = await repo.get_po_by_ids(["p1", "p2", "p3"])

    assert len(products) == 3
    assert {p.id for p in products} == {"p1", "p2", "p3"}
    assert all(p.name.startswith("Product") for p in products)


@pytest.mark.asyncio
async def test_get_po_by_ids_partial(setup_db):
    """Test batch retrieval with some missing IDs."""
    repo, _ = await setup_db.__anext__()

    # Mix of existing and non-existing IDs
    products = await repo.get_po_by_ids(["p1", "p999", "p2"])

    assert len(products) == 2
    assert {p.id for p in products} == {"p1", "p2"}


@pytest.mark.asyncio
async def test_get_po_by_ids_empty(setup_db):
    """Test batch retrieval with empty list."""
    repo, _ = await setup_db.__anext__()

    products = await repo.get_po_by_ids([])

    assert len(products) == 0


@pytest.mark.asyncio
async def test_exists_po_by_id_true(setup_db):
    """Test ID existence check for existing entity."""
    repo, _ = await setup_db.__anext__()

    exists = await repo.exists_po_by_id("p1")

    assert exists is True


@pytest.mark.asyncio
async def test_exists_po_by_id_false(setup_db):
    """Test ID existence check for non-existing entity."""
    repo, _ = await setup_db.__anext__()

    exists = await repo.exists_po_by_id("p999")

    assert exists is False


@pytest.mark.asyncio
async def test_delete_po_by_ids_success(setup_db):
    """Test batch deletion by IDs."""
    repo, _ = await setup_db.__anext__()

    # Delete multiple products
    deleted_count = await repo.delete_po_by_ids(["p1", "p2"])

    assert deleted_count == 2

    # Verify deletion
    exists_p1 = await repo.exists_po_by_id("p1")
    exists_p2 = await repo.exists_po_by_id("p2")
    exists_p3 = await repo.exists_po_by_id("p3")

    assert exists_p1 is False
    assert exists_p2 is False
    assert exists_p3 is True  # Not deleted


@pytest.mark.asyncio
async def test_delete_po_by_ids_partial(setup_db):
    """Test batch deletion with some non-existing IDs."""
    repo, _ = await setup_db.__anext__()

    # Mix of existing and non-existing IDs
    deleted_count = await repo.delete_po_by_ids(["p1", "p999", "p2"])

    assert deleted_count == 2  # Only existing ones deleted


@pytest.mark.asyncio
async def test_delete_po_by_ids_empty(setup_db):
    """Test batch deletion with empty list."""
    repo, _ = await setup_db.__anext__()

    deleted_count = await repo.delete_po_by_ids([])

    assert deleted_count == 0
