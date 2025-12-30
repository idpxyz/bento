"""Dependency injection integration for Bento Runtime."""

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bento.runtime.bootstrap import BentoRuntime

logger = logging.getLogger(__name__)


class DIIntegration:
    """Manages dependency injection for FastAPI integration."""

    def __init__(self, runtime: "BentoRuntime") -> None:
        """Initialize DI integration.

        Args:
            runtime: BentoRuntime instance
        """
        self.runtime = runtime

    def get_uow(self) -> Any:
        """Get the UnitOfWork dependency function for FastAPI.

        Returns:
            FastAPI Depends-compatible async generator function

        Example:
            ```python
            @router.post("/products")
            async def create_product(uow: UnitOfWork = Depends(runtime.get_uow)):
                result = await handler.handle(command, uow)
                return result
            ```
        """
        if self.runtime._get_uow_func is not None:
            return self.runtime._get_uow_func

        if not self.runtime._session_factory:
            raise RuntimeError(
                "Database not configured. Cannot create UnitOfWork dependency. "
                "Configure database with RuntimeBuilder.with_database()"
            )

        async def get_uow_impl():
            from bento.persistence.outbox import SqlAlchemyOutbox
            from bento.persistence.uow import SQLAlchemyUnitOfWork

            session = self.runtime._session_factory()
            try:
                # Create outbox for transactional event publishing
                outbox = SqlAlchemyOutbox(session)

                # Get repository factories if available
                repo_factories = {}
                if hasattr(self.runtime, 'repository_registry'):
                    repo_factories = self.runtime.repository_registry._factories

                # Create UoW with proper implementation
                uow = SQLAlchemyUnitOfWork(
                    session=session,
                    outbox=outbox,
                    repository_factories=repo_factories,
                    event_bus=self.runtime._event_bus,
                )

                # Register ports if available
                if hasattr(self.runtime, 'port_registry'):
                    for port_type, factory in self.runtime.port_registry._factories.items():
                        uow.register_port(port_type, factory)

                yield uow
            finally:
                await session.close()

        self.runtime._get_uow_func = get_uow_impl
        return self.runtime._get_uow_func

    def get_repository_dependency(self, aggregate_class: type[Any]) -> Any:
        """Get repository dependency function for a specific aggregate.

        Args:
            aggregate_class: Aggregate root class

        Returns:
            FastAPI Depends-compatible async generator function

        Example:
            ```python
            @router.get("/products/{id}")
            async def get_product(
                id: str,
                product_repo = Depends(runtime.get_repository(Product))
            ):
                product = await product_repo.get(id)
                return product
            ```
        """
        async def get_repository_impl():
            from bento.persistence.outbox import SqlAlchemyOutbox
            from bento.persistence.uow import SQLAlchemyUnitOfWork

            session = self.runtime._session_factory()
            try:
                outbox = SqlAlchemyOutbox(session)
                repo_factories = {}
                if hasattr(self.runtime, 'repository_registry'):
                    repo_factories = self.runtime.repository_registry._factories

                uow = SQLAlchemyUnitOfWork(
                    session=session,
                    outbox=outbox,
                    repository_factories=repo_factories,
                    event_bus=self.runtime._event_bus,
                )
                repo = uow.repository(aggregate_class)
                yield repo
            finally:
                await session.close()

        return get_repository_impl

    def get_event_bus(self) -> Any:
        """Get EventBus dependency function for FastAPI.

        Returns:
            FastAPI Depends-compatible function

        Example:
            ```python
            @router.post("/products")
            async def create_product(
                event_bus = Depends(runtime.get_event_bus)
            ):
                event = ProductCreated(...)
                await event_bus.publish(event)
            ```
        """
        def get_event_bus_impl() -> Any:
            if not self.runtime._event_bus:
                logger.warning("EventBus not configured, returning None")
                return None
            return self.runtime._event_bus

        return get_event_bus_impl

    def get_handler_dependency(self) -> Any:
        """Get the handler dependency function for FastAPI.

        Note: This is a legacy method. In most cases, you should
        instantiate handlers directly with their dependencies.

        Returns:
            FastAPI Depends-compatible function

        Example:
            ```python
            # Recommended approach:
            @router.post("/products")
            async def create_product(
                command: CreateProductCommand,
                uow: UnitOfWork = Depends(runtime.get_uow)
            ):
                handler = CreateProductHandler(uow)
                result = await handler.handle(command)
                return result

            # Legacy approach (not recommended):
            async def create_product(
                handler = Depends(runtime.handler_dependency)
            ):
                ...
            ```
        """
        if self.runtime._handler_dependency_func is not None:
            return self.runtime._handler_dependency_func

        logger.warning(
            "handler_dependency is a legacy feature. "
            "Consider instantiating handlers directly with their dependencies."
        )

        def handler_dependency_impl() -> dict[str, Any]:
            """Return a dict of common dependencies for handlers."""
            return {
                "uow_factory": self.runtime._uow_factory,
                "event_bus": self.runtime._event_bus,
                "container": self.runtime.container,
            }

        self.runtime._handler_dependency_func = handler_dependency_impl
        return self.runtime._handler_dependency_func

    def get_container(self) -> Any:
        """Get the DI container dependency function for FastAPI.

        Returns:
            FastAPI Depends-compatible function

        Example:
            ```python
            @router.get("/config")
            async def get_config(
                container = Depends(runtime.get_container)
            ):
                config = container.get("config")
                return config
            ```
        """
        def get_container_impl():
            return self.runtime.container

        return get_container_impl
