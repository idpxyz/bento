import pytest

from bento.core.ids import ID
from bento.domain.entity import Entity
from bento.persistence.repository import InMemoryRepository  # type: ignore[attr-defined]


class User(Entity):
    name: str  # type: ignore[assignment]


@pytest.mark.asyncio
async def test_inmemory_repository_crud():
    repo = InMemoryRepository[User]()

    u1 = User(id=ID.generate())
    u1.name = "Alice"  # type: ignore[attr-defined]

    # save
    await repo.save(u1)

    # get by raw id
    got = await repo.get(u1.id)
    assert got is not None and got.name == "Alice"  # type: ignore[attr-defined]

    # list
    all_items = await repo.list()
    assert len(all_items) == 1

    # overwrite on save
    u1.name = "Bob"  # type: ignore[attr-defined]
    await repo.save(u1)
    got2 = await repo.get(u1.id)
    assert got2 is not None and got2.name == "Bob"  # type: ignore[attr-defined]
