"""UnitOfWork Port - Application layer contract for transaction management.

This module defines the UnitOfWork protocol for managing transactions and
coordinating changes across multiple aggregates.

The Unit of Work pattern ensures that:
1. Multiple changes are committed atomically
2. Domain events are collected and published after successful commit
3. Changes are rolled back on failure
"""

from collections.abc import Callable
from typing import Any, Protocol, TypeVar

from bento.core.ids import EntityId
from bento.domain.aggregate import AggregateRoot
from bento.domain.domain_event import DomainEvent
from bento.domain.ports.repository import IRepository

AR = TypeVar("AR", bound=AggregateRoot)
T = TypeVar("T")


class UnitOfWork(Protocol):
    """UnitOfWork protocol - defines the contract for transaction management.

    The Unit of Work pattern coordinates:
    - Transaction boundaries (begin, commit, rollback)
    - Aggregate change tracking
    - Domain event collection and publishing
    - Resource provisioning (repositories and outbound ports)

    This is a Protocol (not ABC), enabling structural subtyping.

    UoW acts as a Transaction Context and Resource Provider:
    - Repositories: uow.repository(AggregateType) for data access
    - Ports: uow.port(PortType) for cross-BC services and external adapters

    This is NOT a Service Locator anti-pattern because:
    - Scope is limited to transaction-relevant resources
    - Ports are interfaces defined by the application layer
    - Dependencies are explicit via Port interfaces

    Type-safe usage with async context manager ensures proper resource cleanup.

    Example:
        ```python
        # In a command handler
        class CreateOrderHandler:
            def __init__(self, uow: UnitOfWork):
                self.uow = uow

            async def execute(self, cmd: CreateOrderCommand) -> Order:
                async with self.uow:
                    # Get port for cross-BC service
                    product_catalog = self.uow.port(IProductCatalogService)
                    await product_catalog.check_products_available(...)
                    
                    # Get repository for data access
                    order_repo = self.uow.repository(Order)
                    order = Order.create(...)
                    await order_repo.save(order)
                    
                    await self.uow.commit()  # Auto-publishes events
                return order
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

    def register_port(self, port_type: type, factory: Callable[[Any], Any]) -> None:
        """Register an outbound port implementation (adapter) factory.

        Ports are interfaces defined in the domain/application layer that the
        application depends on. This method registers the infrastructure
        implementation (adapter) that will be provided at runtime.

        Args:
            port_type: The port interface type (e.g., IProductCatalogService)
            factory: Function that creates the adapter instance

        Example:
            ```python
            # In composition root (dependencies.py)
            uow.register_port(
                IProductCatalogService,
                lambda s: ProductCatalogAdapter(s)
            )
            ```

        Note:
            Only register ports relevant to the current BC's transaction context.
            Don't use this for global infrastructure services.
        """
        ...

    def port(self, port_type: type[T]) -> T:
        """Get the implementation (adapter) for an outbound port.

        This provides lazy-loaded adapter instances for ports defined by
        the application layer. The adapter is created on first access and
        cached for the lifetime of the UoW.

        Args:
            port_type: The port interface type

        Returns:
            Adapter instance implementing the port interface

        Raises:
            ValueError: If no adapter registered for the port type

        Example:
            ```python
            # In application handler
            product_catalog = self.uow.port(IProductCatalogService)
            available, unavailable = await product_catalog.check_products_available([...])
            ```

        Architecture:
            Application Layer → depends on → Port Interface (IProductCatalogService)
                                                ↑
            Infrastructure Layer → implements → Adapter (ProductCatalogAdapter)
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
