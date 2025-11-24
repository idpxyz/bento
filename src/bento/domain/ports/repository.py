"""Repository Port - Domain layer contract for data persistence.

This module defines the Repository protocol that the domain layer depends on.
All repository implementations must conform to this protocol.

The repository pattern provides an abstraction over data access, allowing the
domain layer to remain independent of persistence implementation details.

In DDD, repositories provide access to Aggregate Roots only, not arbitrary entities.
"""

from typing import Protocol

from bento.core.ids import EntityId
from bento.domain.aggregate import AggregateRoot


class Repository[AR: AggregateRoot, ID: EntityId](Protocol):
    """Repository protocol - defines the contract for aggregate root persistence.

    This is a Protocol (not an abstract base class), which means:
    1. No inheritance required - structural subtyping
    2. Type checkers can verify implementations
    3. Domain layer doesn't depend on concrete implementations

    Important - DDD Principle:
        Repositories operate on Aggregate Roots only.
        Entities within an aggregate are accessed through their aggregate root.
        This enforces proper aggregate boundaries and maintains consistency.

    Type Parameters:
        AR: Aggregate Root type (must extend AggregateRoot)
        ID: Aggregate Root ID type

    Example:
        ```python
        # Domain layer defines the contract
        class UserRepository(Repository[User, UserId], Protocol):
            async def find_by_email(self, email: str) -> User | None:
                ...

        # Infrastructure layer implements it
        class SqlUserRepository:
            async def get(self, id: UserId) -> User | None:
                # SQLAlchemy implementation
                ...
        ```
    """

    async def get(self, id: ID) -> AR | None:
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

    async def save(self, aggregate: AR) -> AR:
        """Save an aggregate root (create or update).

        This method handles both create and update operations. The repository
        implementation should detect whether the aggregate is new or existing.

        Note: In DDD, Repository operates on Aggregate Roots, not arbitrary entities.
        The aggregate root is the entry point to the aggregate.

        Args:
            aggregate: The aggregate root to save

        Returns:
            The saved aggregate root (may include generated values like timestamps)

        Raises:
            May raise domain-specific errors (e.g., validation, conflicts)

        Example:
            ```python
            user = User.create(name="Alice", email="alice@example.com")
            saved_user = await repo.save(user)
            ```
        """
        ...

    async def delete(self, aggregate: AR) -> None:
        """Delete an aggregate root.

        Args:
            aggregate: The aggregate root to delete

        Note:
            Some implementations may use soft delete (logical deletion)
            instead of hard delete (physical removal).

            In DDD, deleting an aggregate root should also handle
            the deletion of all entities within the aggregate boundary.

        Example:
            ```python
            await repo.delete(user)
            ```
        """
        ...

    async def find_all(self) -> list[AR]:
        """Find all aggregate roots.

        Returns:
            List of all aggregate roots (may be empty)

        Warning:
            This method may be inefficient for large datasets.
            Consider using pagination or specifications for production use.

            In DDD, this returns aggregate roots, not all entities.
            Entities within aggregates are accessed through their aggregate root.

        Example:
            ```python
            all_users = await repo.find_all()
            ```
        """
        ...

    async def exists(self, id: ID) -> bool:
        """Check if an aggregate root exists by ID.

        Args:
            id: The aggregate root ID to check

        Returns:
            True if aggregate root exists, False otherwise

        Example:
            ```python
            if await repo.exists(user_id):
                print("User exists")
            ```
        """
        ...

    async def count(self) -> int:
        """Count total number of aggregate roots.

        Returns:
            Total count of aggregate roots

        Example:
            ```python
            total = await repo.count()
            print(f"Total users: {total}")
            ```
        """
        ...
