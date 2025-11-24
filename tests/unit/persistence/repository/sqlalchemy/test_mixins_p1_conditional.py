"""Unit tests for ConditionalUpdateMixin (P1).

Tests conditional update/delete operations:
- update_po_by_spec
- delete_po_by_spec
- soft_delete_po_by_spec
- restore_po_by_spec
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
from bento.persistence.specification import CompositeSpecification


class TestBase(DeclarativeBase):
    pass


class TaskPO(TestBase):
    __tablename__ = "t_task"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class StatusSpec(CompositeSpecification):
    """Simple specification for filtering by status."""

    def __init__(self, status: str):
        self._status = status

    def apply(self, query, po_type):
        return query.where(po_type.status == self._status)


@pytest.fixture
async def setup_db():
    """Setup test database and repository."""
    engine: AsyncEngine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    try:
        async with engine.begin() as conn:
            await conn.run_sync(TestBase.metadata.create_all)

        async with async_session() as session:
            repo = BaseRepository[TaskPO, str](
                session=session,
                po_type=TaskPO,
                actor="tester",
                interceptor_chain=None,
            )

            # Create test data
            tasks = [
                TaskPO(id="t1", title="Task 1", status="pending"),
                TaskPO(id="t2", title="Task 2", status="pending"),
                TaskPO(id="t3", title="Task 3", status="in_progress"),
                TaskPO(id="t4", title="Task 4", status="completed"),
                TaskPO(id="t5", title="Task 5", status="pending"),
            ]
            for t in tasks:
                await repo.create_po(t)

            yield repo, session

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_update_po_by_spec(setup_db):
    """Test bulk update by specification."""
    repo, _ = await setup_db.__anext__()

    # Update all pending tasks to in_progress
    spec = StatusSpec("pending")
    count = await repo.update_po_by_spec(spec, {"status": "in_progress"})

    assert count == 3  # t1, t2, t5

    # Verify updates
    t1 = await repo.get_po_by_id("t1")
    t3 = await repo.get_po_by_id("t3")
    assert t1.status == "in_progress"
    assert t3.status == "in_progress"  # Was already in_progress


@pytest.mark.asyncio
async def test_update_po_by_spec_no_matches(setup_db):
    """Test bulk update with no matching entities."""
    repo, _ = await setup_db.__anext__()

    spec = StatusSpec("archived")
    count = await repo.update_po_by_spec(spec, {"status": "deleted"})

    assert count == 0


@pytest.mark.asyncio
async def test_update_po_by_spec_empty_updates(setup_db):
    """Test bulk update with empty updates dict."""
    repo, _ = await setup_db.__anext__()

    spec = StatusSpec("pending")
    count = await repo.update_po_by_spec(spec, {})

    assert count == 0


@pytest.mark.asyncio
async def test_delete_po_by_spec(setup_db):
    """Test bulk delete by specification."""
    repo, _ = await setup_db.__anext__()

    # Delete all completed tasks
    spec = StatusSpec("completed")
    count = await repo.delete_po_by_spec(spec)

    assert count == 1  # t4

    # Verify deletion
    t4 = await repo.get_po_by_id("t4")
    assert t4 is None

    # Verify others remain
    t1 = await repo.get_po_by_id("t1")
    assert t1 is not None


@pytest.mark.asyncio
async def test_delete_po_by_spec_multiple(setup_db):
    """Test bulk delete affecting multiple entities."""
    repo, _ = await setup_db.__anext__()

    # Delete all pending tasks
    spec = StatusSpec("pending")
    count = await repo.delete_po_by_spec(spec)

    assert count == 3  # t1, t2, t5

    # Verify remaining count
    remaining = await repo.count_po_by_spec(None)  # type: ignore
    assert remaining == 2  # t3, t4


@pytest.mark.asyncio
async def test_soft_delete_po_by_spec(setup_db):
    """Test soft delete by specification."""
    repo, session = await setup_db.__anext__()

    # Soft delete all pending tasks
    spec = StatusSpec("pending")
    count = await repo.soft_delete_po_by_spec(spec)

    assert count == 3

    # Expire all instances to force reload from database
    session.expire_all()

    # Verify soft deletion (deleted_at is set)
    t1 = await repo.get_po_by_id("t1")
    assert t1 is not None
    assert t1.deleted_at is not None


@pytest.mark.asyncio
async def test_restore_po_by_spec(setup_db):
    """Test restore soft-deleted entities by specification."""
    repo, _ = await setup_db.__anext__()

    # First soft delete
    spec = StatusSpec("pending")
    await repo.soft_delete_po_by_spec(spec)

    # Then restore
    count = await repo.restore_po_by_spec(spec)

    assert count == 3

    # Verify restoration
    t1 = await repo.get_po_by_id("t1")
    assert t1 is not None
    assert t1.deleted_at is None
