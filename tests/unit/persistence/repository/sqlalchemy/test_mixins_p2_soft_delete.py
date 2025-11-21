"""Unit tests for SoftDeleteEnhancedMixin (P2).

Tests soft delete query operations:
- find_trashed_po
- find_with_trashed_po
- count_trashed_po
- is_trashed_po
"""

from datetime import datetime

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


class DocumentPO(TestBase):
    __tablename__ = "t_document"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


@pytest.fixture
async def setup_db():
    """Setup test database and repository."""
    engine: AsyncEngine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    try:
        async with engine.begin() as conn:
            await conn.run_sync(TestBase.metadata.create_all)

        async with async_session() as session:
            repo = BaseRepository[DocumentPO, str](
                session=session,
                po_type=DocumentPO,
                actor="tester",
                interceptor_chain=None,
            )

            # Create test data
            docs = [
                DocumentPO(id="d1", title="Doc 1", deleted_at=None),
                DocumentPO(id="d2", title="Doc 2", deleted_at=None),
                DocumentPO(id="d3", title="Doc 3", deleted_at=datetime(2025, 1, 1)),
                DocumentPO(id="d4", title="Doc 4", deleted_at=datetime(2025, 1, 2)),
                DocumentPO(id="d5", title="Doc 5", deleted_at=None),
            ]
            for d in docs:
                await repo.create_po(d)

            yield repo, session

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_find_trashed_po(setup_db):
    """Test finding all soft-deleted entities."""
    repo, _ = await setup_db.__anext__()

    trashed = await repo.find_trashed_po()

    assert len(trashed) == 2
    assert {d.id for d in trashed} == {"d3", "d4"}
    assert all(d.deleted_at is not None for d in trashed)


@pytest.mark.asyncio
async def test_find_with_trashed_po(setup_db):
    """Test finding all entities including soft-deleted ones."""
    repo, _ = await setup_db.__anext__()

    all_docs = await repo.find_with_trashed_po()

    assert len(all_docs) == 5
    assert {d.id for d in all_docs} == {"d1", "d2", "d3", "d4", "d5"}


@pytest.mark.asyncio
async def test_count_trashed_po(setup_db):
    """Test counting soft-deleted entities."""
    repo, _ = await setup_db.__anext__()

    count = await repo.count_trashed_po()

    assert count == 2


@pytest.mark.asyncio
async def test_is_trashed_po_true(setup_db):
    """Test checking if entity is soft-deleted (true)."""
    repo, _ = await setup_db.__anext__()

    is_trashed = await repo.is_trashed_po("d3")

    assert is_trashed is True


@pytest.mark.asyncio
async def test_is_trashed_po_false(setup_db):
    """Test checking if entity is soft-deleted (false)."""
    repo, _ = await setup_db.__anext__()

    is_trashed = await repo.is_trashed_po("d1")

    assert is_trashed is False


@pytest.mark.asyncio
async def test_is_trashed_po_nonexistent(setup_db):
    """Test checking if non-existent entity is soft-deleted."""
    repo, _ = await setup_db.__anext__()

    is_trashed = await repo.is_trashed_po("d999")

    assert is_trashed is False


@pytest.mark.asyncio
async def test_find_trashed_po_empty_result():
    """Test finding trashed entities when none exist."""
    engine: AsyncEngine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    try:
        async with engine.begin() as conn:
            await conn.run_sync(TestBase.metadata.create_all)

        async with async_session() as session:
            repo = BaseRepository[DocumentPO, str](
                session=session,
                po_type=DocumentPO,
                actor="tester",
                interceptor_chain=None,
            )

            # Create only active documents
            await repo.create_po(DocumentPO(id="d1", title="Doc 1"))

            trashed = await repo.find_trashed_po()
            count = await repo.count_trashed_po()

            assert len(trashed) == 0
            assert count == 0

    finally:
        await engine.dispose()
