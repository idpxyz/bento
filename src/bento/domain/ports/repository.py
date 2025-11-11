"""Repository Port - Domain layer contract for data persistence.

This module defines the Repository protocol that the domain layer depends on.
All repository implementations must conform to this protocol.

The repository pattern provides an abstraction over data access, allowing the
domain layer to remain independent of persistence implementation details.
"""

from typing import Protocol

from bento.core.ids import EntityId
from bento.domain.entity import Entity


class Repository[E: Entity, ID: EntityId](Protocol):
    """Repository protocol - defines the contract for entity persistence.

    This is a Protocol (not an abstract base class), which means:
    1. No inheritance required - structural subtyping
    2. Type checkers can verify implementations
    3. Domain layer doesn't depend on concrete implementations

    Type Parameters:
        E: Entity type (contravariant)
        ID: Entity ID type

    Example:
        ```python
        # Domain layer defines the contract
        class UserRepository(Protocol):
            async def get(self, id: UserId) -> Optional[User]:
                ...

        # Infrastructure layer implements it
        class SqlUserRepository:
            async def get(self, id: UserId) -> Optional[User]:
                # SQLAlchemy implementation
                ...
        ```
    """

    async def get(self, id: ID) -> E | None:
        """Get an entity by its ID.

        Args:
            id: The entity ID to search for

        Returns:
            The entity if found, None otherwise

        Example:
            ```python
            user = await repo.get(UserId("123"))
            if user:
                print(f"Found: {user.name}")
            ```
        """
        ...

    async def save(self, entity: E) -> E:
        """Save an entity (create or update).

        This method handles both create and update operations. The repository
        implementation should detect whether the entity is new or existing.

        Args:
            entity: The entity to save

        Returns:
            The saved entity (may include generated values like timestamps)

        Raises:
            May raise domain-specific errors (e.g., validation, conflicts)

        Example:
            ```python
            user = User.create(name="Alice", email="alice@example.com")
            saved_user = await repo.save(user)
            ```
        """
        ...

    async def delete(self, entity: E) -> None:
        """Delete an entity.

        Args:
            entity: The entity to delete

        Note:
            Some implementations may use soft delete (logical deletion)
            instead of hard delete (physical removal).

        Example:
            ```python
            await repo.delete(user)
            ```
        """
        ...

    async def find_all(self) -> list[E]:
        """Find all entities.

        Returns:
            List of all entities (may be empty)

        Warning:
            This method may be inefficient for large datasets.
            Consider using pagination or specifications for production use.

        Example:
            ```python
            all_users = await repo.find_all()
            ```
        """
        ...

    async def exists(self, id: ID) -> bool:
        """Check if an entity exists by ID.

        Args:
            id: The entity ID to check

        Returns:
            True if entity exists, False otherwise

        Example:
            ```python
            if await repo.exists(user_id):
                print("User exists")
            ```
        """
        ...

    async def count(self) -> int:
        """Count total number of entities.

        Returns:
            Total count of entities

        Example:
            ```python
            total = await repo.count()
            print(f"Total users: {total}")
            ```
        """
        ...
