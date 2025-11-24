"""Domain Service base class.

Domain Services encapsulate business logic that doesn't naturally fit within
a single Entity or Value Object. They typically coordinate multiple aggregates
or perform operations that span multiple entities.
"""

from typing import TypeVar

from bento.core.ids import EntityId
from bento.domain.aggregate import AggregateRoot
from bento.domain.ports.repository import IRepository

AR = TypeVar("AR", bound=AggregateRoot)
ID = TypeVar("ID", bound=EntityId)


class DomainService[AR: AggregateRoot, ID: EntityId]:
    """Base class for domain services.

    Domain services contain business logic that:
    - Doesn't naturally belong to a single entity
    - Coordinates multiple aggregates
    - Performs calculations or validations across entities

    This base class provides common repository operations that most
    domain services need.

    Example:
        ```python
        class TransferService(DomainService[Account, str]):
            async def transfer(
                self,
                from_id: str,
                to_id: str,
                amount: Decimal
            ) -> bool:
                # Get both accounts
                from_account = await self.get(from_id)
                to_account = await self.get(to_id)

                if not from_account or not to_account:
                    return False

                # Perform transfer (domain logic)
                from_account.withdraw(amount)
                to_account.deposit(amount)

                # Save both
                await self.save(from_account)
                await self.save(to_account)

                return True
        ```
    """

    def __init__(self, repository: IRepository[AR, ID]) -> None:
        """Initialize domain service with repository.

        Args:
            repository: Repository for accessing entities
        """
        self._repository = repository

    async def get(self, entity_id: ID) -> AR | None:
        """Get entity by ID.

        Args:
            entity_id: Entity identifier

        Returns:
            Entity if found, None otherwise
        """
        return await self._repository.get(entity_id)

    async def save(self, entity: AR) -> AR:
        """Save entity.

        Args:
            entity: Entity to save

        Returns:
            Saved entity
        """
        return await self._repository.save(entity)

    async def exists(self, entity_id: ID) -> bool:
        """Check if entity exists.

        Args:
            entity_id: Entity identifier

        Returns:
            True if entity exists
        """
        return await self._repository.exists(entity_id)

    async def delete(self, entity: AR) -> None:
        """Delete entity.

        Args:
            entity: Entity to delete
        """
        await self._repository.delete(entity)
