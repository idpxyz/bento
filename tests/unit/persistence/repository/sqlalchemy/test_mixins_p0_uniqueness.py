"""Unit tests for UniquenessChecksMixin (P0).

Tests uniqueness validation and field queries:
- is_field_unique_po
- find_po_by_field
- find_all_po_by_field
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


class UserPO(TestBase):
    __tablename__ = "t_user"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False, default="user")


@pytest.fixture
async def setup_db():
    """Setup test database and repository."""
    engine: AsyncEngine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    try:
        async with engine.begin() as conn:
            await conn.run_sync(TestBase.metadata.create_all)

        async with async_session() as session:
            repo = BaseRepository[UserPO, str](
                session=session,
                po_type=UserPO,
                actor="tester",
                interceptor_chain=None,
            )

            # Create test data
            users = [
                UserPO(id="u1", email="alice@example.com", name="Alice", role="admin"),
                UserPO(id="u2", email="bob@example.com", name="Bob", role="user"),
                UserPO(id="u3", email="charlie@example.com", name="Charlie", role="user"),
                UserPO(id="u4", email="david@example.com", name="David", role="admin"),
            ]
            for u in users:
                await repo.create_po(u)

            yield repo, session

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_is_field_unique_po_true(setup_db):
    """Test uniqueness check for non-existing value."""
    repo, _ = await setup_db.__anext__()

    is_unique = await repo.is_field_unique_po("email", "new@example.com")

    assert is_unique is True


@pytest.mark.asyncio
async def test_is_field_unique_po_false(setup_db):
    """Test uniqueness check for existing value."""
    repo, _ = await setup_db.__anext__()

    is_unique = await repo.is_field_unique_po("email", "alice@example.com")

    assert is_unique is False


@pytest.mark.asyncio
async def test_is_field_unique_po_exclude_self(setup_db):
    """Test uniqueness check excluding current entity (for updates)."""
    repo, _ = await setup_db.__anext__()

    # Should be unique when excluding self
    is_unique = await repo.is_field_unique_po("email", "alice@example.com", exclude_id="u1")

    assert is_unique is True


@pytest.mark.asyncio
async def test_is_field_unique_po_exclude_self_still_duplicate(setup_db):
    """Test uniqueness check excluding self but still found duplicate."""
    repo, _ = await setup_db.__anext__()

    # alice@example.com exists for u1, checking from u2's perspective
    is_unique = await repo.is_field_unique_po("email", "alice@example.com", exclude_id="u2")

    assert is_unique is False


@pytest.mark.asyncio
async def test_find_po_by_field_found(setup_db):
    """Test finding entity by field value."""
    repo, _ = await setup_db.__anext__()

    user = await repo.find_po_by_field("email", "bob@example.com")

    assert user is not None
    assert user.id == "u2"
    assert user.name == "Bob"


@pytest.mark.asyncio
async def test_find_po_by_field_not_found(setup_db):
    """Test finding non-existing entity by field."""
    repo, _ = await setup_db.__anext__()

    user = await repo.find_po_by_field("email", "nonexistent@example.com")

    assert user is None


@pytest.mark.asyncio
async def test_find_all_po_by_field_multiple(setup_db):
    """Test finding all entities by field value (multiple matches)."""
    repo, _ = await setup_db.__anext__()

    users = await repo.find_all_po_by_field("role", "user")

    assert len(users) == 2
    assert {u.id for u in users} == {"u2", "u3"}
    assert all(u.role == "user" for u in users)


@pytest.mark.asyncio
async def test_find_all_po_by_field_single(setup_db):
    """Test finding all entities by unique field value (single match)."""
    repo, _ = await setup_db.__anext__()

    users = await repo.find_all_po_by_field("email", "alice@example.com")

    assert len(users) == 1
    assert users[0].id == "u1"


@pytest.mark.asyncio
async def test_find_all_po_by_field_none(setup_db):
    """Test finding entities with no matches."""
    repo, _ = await setup_db.__anext__()

    users = await repo.find_all_po_by_field("role", "superadmin")

    assert len(users) == 0
