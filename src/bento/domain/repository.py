from typing import Protocol, TypeVar

from bento.core.ids import EntityId

T = TypeVar("T")


class Repository[T](Protocol):
    """Base repository protocol defining core CRUD operations.

    This protocol defines the minimum contract that all repositories must implement.
    Specific repositories can extend this with additional query methods.

    Methods:
        get / find_by_id: Retrieve single entity by ID (semantically equivalent)
        save: Persist entity (create or update)
        list: Retrieve all entities
    """

    async def get(self, id: EntityId) -> T | None:
        """Retrieve entity by ID.

        Args:
            id: Entity identifier

        Returns:
            Entity if found, None otherwise
        """
        ...

    async def find_by_id(self, id: EntityId) -> T | None:
        """Alias for get() with more explicit naming.

        Args:
            id: Entity identifier

        Returns:
            Entity if found, None otherwise
        """
        ...

    async def save(self, entity: T) -> None:
        """Persist entity (create or update).

        Args:
            entity: Entity to persist
        """
        ...

    async def list(self) -> list[T]:
        """Retrieve all entities.

        Returns:
            List of all entities
        """
        ...
