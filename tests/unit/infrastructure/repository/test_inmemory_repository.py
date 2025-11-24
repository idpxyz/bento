import pytest

from bento.core.ids import ID
from bento.domain.aggregate import AggregateRoot
from bento.infrastructure.repository import InMemoryRepository


class User(AggregateRoot):
    """Test aggregate root."""

    name: str  # type: ignore[assignment]


@pytest.mark.asyncio
async def test_inmemory_repository_crud():
    repo = InMemoryRepository[User]()

    u1 = User(id=ID.generate())
    u1.name = "Alice"  # type: ignore[attr-defined]

    # save
    saved = await repo.save(u1)
    assert saved is u1

    # get by raw id
    got = await repo.get(u1.id)
    assert got is not None and got.name == "Alice"  # type: ignore[attr-defined]

    # find_all
    all_items = await repo.find_all()
    assert len(all_items) == 1

    # exists
    assert await repo.exists(u1.id)

    # count
    assert await repo.count() == 1

    # overwrite on save
    u1.name = "Bob"  # type: ignore[attr-defined]
    await repo.save(u1)
    got2 = await repo.get(u1.id)
    assert got2 is not None and got2.name == "Bob"  # type: ignore[attr-defined]

    # delete
    await repo.delete(u1)
    assert await repo.get(u1.id) is None
    assert await repo.count() == 0
