from bento.core.ids import EntityId
from bento.domain.entity import Entity
from bento.domain.ports.repository import Repository


class InMemoryRepository[T: Entity](Repository[T, EntityId]):
    def __init__(self):
        self._store: dict[str, T] = {}

    async def get(self, id: EntityId) -> T | None:
        return self._store.get(id.value)

    async def save(self, entity: T) -> None:
        # entity must have id: EntityId
        self._store[entity.id.value] = entity

    async def list(self) -> list[T]:
        return list(self._store.values())
