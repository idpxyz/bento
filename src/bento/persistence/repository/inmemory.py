"""In-memory repository implementation for testing and simple use cases.

This repository stores aggregate roots in memory (dict) and is useful for:
- Unit tests
- Prototyping
- Simple applications that don't need persistence
"""

from __future__ import annotations

from bento.core.ids import EntityId
from bento.domain.aggregate import AggregateRoot
from bento.domain.ports.repository import Repository


class InMemoryRepository[AR: AggregateRoot](Repository[AR, EntityId]):
    """In-memory repository implementation.

    Stores aggregate roots in a dictionary keyed by ID.
    Not thread-safe and data is lost when the process terminates.
    """

    def __init__(self) -> None:
        self._store: dict[str, AR] = {}

    async def get(self, id: EntityId) -> AR | None:
        """Get aggregate root by ID."""
        return self._store.get(id.value)

    async def save(self, aggregate: AR) -> AR:
        """Save aggregate root and return it."""
        self._store[aggregate.id.value] = aggregate
        return aggregate

    async def delete(self, aggregate: AR) -> None:
        """Delete aggregate root."""
        self._store.pop(aggregate.id.value, None)

    async def find_all(self) -> list[AR]:
        """Find all aggregate roots."""
        return list(self._store.values())

    async def exists(self, id: EntityId) -> bool:
        """Check if aggregate root exists by ID."""
        return id.value in self._store

    async def count(self) -> int:
        """Count total number of aggregate roots."""
        return len(self._store)
