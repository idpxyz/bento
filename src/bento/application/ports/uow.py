"""UnitOfWork Port - Application layer contract for transaction management.

This module defines the UnitOfWork protocol for managing transactions and
coordinating changes across multiple aggregates.

The Unit of Work pattern ensures that:
1. Multiple changes are committed atomically
2. Domain events are collected and published after successful commit
3. Changes are rolled back on failure
"""

from typing import Protocol, TypeVar

from bento.core.ids import EntityId
from bento.domain.aggregate import AggregateRoot
from bento.domain.domain_event import DomainEvent
from bento.domain.ports.repository import IRepository

AR = TypeVar("AR", bound=AggregateRoot)


class UnitOfWork(Protocol):
    """UnitOfWork protocol - defines the contract for transaction management.

    The Unit of Work pattern coordinates:
    - Transaction boundaries (begin, commit, rollback)
    - Aggregate change tracking
    - Domain event collection and publishing

    This is a Protocol (not ABC), enabling structural subtyping.

    Type-safe usage with async context manager ensures proper resource cleanup.

    Example:
        ```python
        # In a use case
        class CreateUserUseCase:
            def __init__(self, uow: UnitOfWork, repo: Repository):
                self.uow = uow
                self.repo = repo

            async def execute(self, cmd: CreateUserCommand) -> Result:
                async with self.uow:
                    user = User.create(...)
                    await self.repo.save(user)
                    await self.uow.commit()  # Auto-publishes events
                return Ok(user.id)
        ```
    """

    pending_events: list[DomainEvent]
    """List of domain events collected from aggregates during this UoW."""

    async def begin(self) -> None:
        """Begin a new transaction/unit of work.

        This method should:
        1. Start a new database transaction
        2. Initialize event collection
        3. Set up any necessary context

        Usually called automatically by __aenter__.

        Example:
            ```python
            await uow.begin()
            try:
                # ... operations ...
                await uow.commit()
            except Exception:
                await uow.rollback()
            ```
        """
        ...

    async def commit(self) -> None:
        """Commit the transaction and publish collected events.

        This method should:
        1. Persist all aggregate changes
        2. Write events to outbox table (for transactional outbox pattern)
        3. Commit the database transaction
        4. Publish events to message bus (or mark for async publishing)

        If commit fails, all changes should be rolled back automatically.

        Raises:
            May raise database or infrastructure errors

        Example:
            ```python
            async with uow:
                user = User.create(...)
                await repo.save(user)
                await uow.commit()  # All or nothing
            ```
        """
        ...

    async def rollback(self) -> None:
        """Rollback the transaction and discard collected events.

        This method should:
        1. Roll back all aggregate changes
        2. Clear collected events
        3. Clean up resources

        Usually called automatically by __aexit__ on exception.

        Example:
            ```python
            try:
                await uow.commit()
            except Exception:
                await uow.rollback()
                raise
            ```
        """
        ...

    async def collect_events(self) -> list[DomainEvent]:
        """Collect domain events from all tracked aggregates.

        This method should:
        1. Pull events from all modified aggregates
        2. Add them to pending_events list
        3. Clear events from aggregates (to prevent double publishing)

        Returns:
            List of collected domain events

        Note:
            Usually called automatically during commit, but can be called
            manually if you need to inspect events before committing.

        Example:
            ```python
            async with uow:
                user = User.create(...)
                await repo.save(user)

                events = await uow.collect_events()
                logger.info(f"Collected {len(events)} events")

                await uow.commit()
            ```
        """
        ...

    def repository(self, aggregate_type: type[AR]) -> IRepository[AR, EntityId]:
        """Get repository for a specific aggregate type.

        Args:
            aggregate_type: The aggregate class type

        Returns:
            Repository instance for the aggregate type

        Example:
            ```python
            async with uow:
                order_repo = uow.repository(Order)
                order = await order_repo.find_by_id(order_id)
                await uow.commit()
            ```
        """
        ...

    async def __aenter__(self) -> "UnitOfWork":
        """Enter the async context manager (calls begin).

        Returns:
            Self for use in async with statement

        Example:
            ```python
            async with uow:
                # Transaction started automatically
                ...
            ```
        """
        ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        """Exit the async context manager.

        Automatically rolls back on exception, or commits if no exception
        (depending on implementation - some implementations require explicit commit).

        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception instance if an exception occurred
            exc_tb: Exception traceback if an exception occurred

        Example:
            ```python
            async with uow:
                # ... operations ...
                await uow.commit()
            # Automatic cleanup on exit
            ```
        """
        ...
