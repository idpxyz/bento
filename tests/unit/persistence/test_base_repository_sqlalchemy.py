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
    __tablename__ = "t_user_po"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)


@pytest.mark.asyncio
async def test_base_repository_crud_and_query():
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

            # Create
            u = UserPO(id="u1", name="Alice")
            await repo.create_po(u)

            # Get
            got = await repo.get_po_by_id("u1")
            assert got is not None and got.name == "Alice"

            # Update
            got.name = "Bob"
            await repo.update_po(got)
            got2 = await repo.get_po_by_id("u1")
            assert got2 is not None and got2.name == "Bob"

            # Count and list (spec is unused in simplified impl)
            cnt = await repo.count_po_by_spec(None)  # type: ignore[arg-type]
            assert cnt == 1
            lst = await repo.query_po_by_spec(None)  # type: ignore[arg-type]
            assert len(lst) == 1

            # Delete
            await repo.delete_po(got2)
            gone = await repo.get_po_by_id("u1")
            assert gone is None
    finally:
        await engine.dispose()
