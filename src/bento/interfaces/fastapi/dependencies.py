"""FastAPI Dependency Injection utilities for Bento Framework.

This module provides dependency injection helpers for integrating Bento's
CQRS handlers with FastAPI routes.

Example:
    ```python
    from bento.interfaces.fastapi import handler_dependency

    @router.post("/orders")
    async def create_order(
        request: CreateOrderRequest,
        handler: Annotated[CreateOrderHandler, handler_dependency(CreateOrderHandler)],
    ):
        command = CreateOrderCommand(...)
        return await handler.execute(command)
    ```
"""

from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Annotated, Any, Callable, Protocol, TypeVar

from bento.application.ports.uow import UnitOfWork

if TYPE_CHECKING:
    from fastapi import Request


class HandlerProtocol(Protocol):
    """Protocol for Handler classes that accept UoW in constructor.

    All CommandHandler and QueryHandler classes follow this protocol.
    """

    def __init__(self, uow: UnitOfWork) -> None: ...


def create_handler_dependency(get_uow_dependency: Callable[..., Any]) -> Callable[[type[HandlerProtocol]], Any]:
    """Create a handler_dependency factory with custom UoW dependency.

    This is the primary way to create handler dependencies in Bento applications.
    It creates a factory function that can be used to inject handlers into
    FastAPI routes with proper UnitOfWork injection.

    Args:
        get_uow_dependency: The FastAPI dependency function that provides UnitOfWork

    Returns:
        A handler_dependency function configured with the custom UoW dependency

    Example:
        ```python
        from bento.interfaces.fastapi import create_handler_dependency
        from shared.infrastructure.dependencies import get_uow

        # Create handler_dependency with your get_uow
        handler_dependency = create_handler_dependency(get_uow)

        # Use in routes
        @router.post("/products")
        async def create_product(
            request: CreateProductRequest,
            handler: Annotated[
                CreateProductHandler,
                handler_dependency(CreateProductHandler)
            ],
        ):
            command = CreateProductCommand(
                name=request.name,
                price=request.price,
            )
            return await handler.execute(command)
        ```

    Note:
        The get_uow dependency should yield a configured UnitOfWork
        with all repositories and ports registered:

        ```python
        async def get_uow(session: AsyncSession = Depends(get_db_session)):
            uow = SQLAlchemyUnitOfWork(session, outbox)
            uow.register_repository(Product, lambda s: ProductRepository(s))
            yield uow
        ```
    """
    try:
        from fastapi import Depends
    except ImportError:
        raise ImportError(
            "FastAPI is required for create_handler_dependency. "
            "Install it with: pip install fastapi"
        )

    THandler = TypeVar("THandler", bound=HandlerProtocol)

    def handler_dependency(handler_cls: type[THandler]) -> Any:
        """Create a FastAPI dependency for a specific Handler class.

        Args:
            handler_cls: The Handler class to instantiate

        Returns:
            A FastAPI Depends instance
        """
        from fastapi import Request

        def factory(
            uow: Annotated[UnitOfWork, Depends(get_uow_dependency)],
            request: Request,
        ) -> THandler:
            # Check if handler needs observability (Observable Handler pattern)
            import inspect
            sig = inspect.signature(handler_cls.__init__)
            params = list(sig.parameters.keys())

            if 'observability' in params:
                # Get observability from runtime
                runtime = getattr(request.app.state, 'bento_runtime', None)
                if runtime:
                    try:
                        observability = runtime.container.get('observability')
                        return handler_cls(uow, observability)  # type: ignore
                    except KeyError:
                        pass
                # Fallback to NoOp if not available
                from bento.adapters.observability.noop import NoOpObservabilityProvider
                noop_observability = NoOpObservabilityProvider()
                return handler_cls(uow, noop_observability)  # type: ignore
            else:
                # Standard handler with only uow
                return handler_cls(uow)
        return Depends(factory)

    return handler_dependency


# =============================================================================
# Global handler_dependency (uses app.state.runtime)
# =============================================================================


async def get_uow_from_runtime(request: "Request") -> AsyncGenerator[UnitOfWork, None]:
    """Get UoW from BentoRuntime stored in app.state.

    This is the standard way to get UoW in Bento applications.
    Requires runtime to be stored in app.state.runtime during startup.

    Note: runtime.get_uow is a FastAPI Depends-compatible function,
    but we need to call the inner generator directly here.
    """
    runtime = request.app.state.runtime

    # runtime.get_uow returns a FastAPI Depends-wrapped function
    # We need to get a session and create UoW manually
    async with runtime._session_factory() as session:
        from bento.persistence.outbox.record import SqlAlchemyOutbox
        from bento.persistence.uow import SQLAlchemyUnitOfWork
        from bento.infrastructure.repository import get_repository_registry
        from bento.infrastructure.ports import get_port_registry

        outbox = SqlAlchemyOutbox(session)
        uow = SQLAlchemyUnitOfWork(
            session,
            outbox,
            event_bus=runtime._event_bus,
        )

        # Auto-register repositories and ports
        for ar_type, repo_cls in get_repository_registry().items():
            uow.register_repository(ar_type, lambda s, cls=repo_cls: cls(s))
        for port_type, adapter_cls in get_port_registry().items():
            uow.register_port(port_type, lambda s, cls=adapter_cls: cls(s))

        yield uow


THandler = TypeVar("THandler", bound=HandlerProtocol)


def handler_dependency(handler_cls: type[THandler]) -> Any:
    """Create a FastAPI Depends for a CommandHandler/QueryHandler.

    This is the recommended way to inject handlers in Bento applications.
    Uses app.state.runtime to get the UoW automatically.

    Usage:
        ```python
        from bento.interfaces.fastapi import handler_dependency

        @router.post("/orders")
        async def create_order(
            handler: Annotated[CreateOrderHandler, handler_dependency(CreateOrderHandler)],
        ):
            return await handler.execute(command)
        ```

    Note:
        Requires BentoRuntime to be stored in app.state.runtime:
        ```python
        app = runtime.create_fastapi_app(...)
        app.state.runtime = runtime
        ```
    """
    try:
        from fastapi import Depends, Request
    except ImportError:
        raise ImportError(
            "FastAPI is required for handler_dependency. "
            "Install it with: pip install fastapi"
        )

    async def factory(request: Request):
        """Create handler with UoW from runtime."""
        runtime = request.app.state.runtime

        # Ensure modules are scanned (triggers @repository_for decorators)
        import importlib
        for module in runtime.registry.resolve_order():
            for pkg in module.scan_packages:
                try:
                    importlib.import_module(pkg)
                except ImportError:
                    pass

        from bento.persistence.outbox.record import SqlAlchemyOutbox
        from bento.persistence.uow import SQLAlchemyUnitOfWork
        from bento.infrastructure.repository import get_repository_registry
        from bento.infrastructure.ports import get_port_registry

        # Get tenant_id from request header
        tenant_id = request.headers.get("X-Tenant-Id", "default")

        async with runtime._session_factory() as session:
            outbox = SqlAlchemyOutbox(session)
            uow = SQLAlchemyUnitOfWork(
                session,
                outbox,
                event_bus=runtime._event_bus,
                tenant_id=tenant_id,
            )

            # Auto-register all discovered repositories
            for ar_type, repo_cls in get_repository_registry().items():
                uow.register_repository(ar_type, lambda s, cls=repo_cls: cls(s))

            # Auto-register all discovered ports
            for port_type, adapter_cls in get_port_registry().items():
                uow.register_port(port_type, lambda s, cls=adapter_cls: cls(s))

            yield handler_cls(uow)

    return Depends(factory)
