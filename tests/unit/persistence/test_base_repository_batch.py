import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import String

from bento.core.ids import ID
from bento.persistence.repository.sqlalchemy.base import BaseRepository


class TestBase(DeclarativeBase):
    pass


class ItemPO(TestBase):
    __tablename__ = "t_item_po"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)


@pytest.mark.asyncio
async def test_base_repository_batch_and_id_wrapper():
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

            # Batch create
            items = [ItemPO(id=f"i{i}", name=f"N{i}") for i in range(3)]
            await repo.batch_po_create(items)
            # Query
            all_pos = await repo.query_po_by_spec(None)  # type: ignore[arg-type]
            assert len(all_pos) == 3

            # Batch update
            for it in items:
                it.name = it.name + "_x"
            await repo.batch_po_update(items)
            got = await repo.get_po_by_id("i0")
            assert got is not None and got.name.endswith("_x")

            # get by ID wrapper
            wrapped = ID("i1")
            got2 = await repo.get_po_by_id(wrapped)  # type: ignore[arg-type]
            assert got2 is not None and got2.id == "i1"

            # Batch delete
            await repo.batch_po_delete(items)
            cnt = await repo.count_po_by_spec(None)  # type: ignore[arg-type]
            assert cnt == 0
    finally:
        await engine.dispose()
