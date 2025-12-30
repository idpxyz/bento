"""FastAPI Dependency Injection utilities for Bento Framework.

This module provides dependency injection helpers for integrating Bento's
CQRS handlers with FastAPI routes.

Performance Optimizations:
    - Handler signature inspection is cached to avoid repeated reflection
    - Module scanning is performed only once (on first request)
    - Handler creation time is logged at DEBUG level for monitoring
    - Observable Handler detection is automatic with zero configuration

Example:
    ```python
    from bento.interfaces.fastapi import handler_dependency

    @router.post("/orders")
    async def create_order(
        request: CreateOrderRequest,
        handler: CreateOrderHandler = handler_dependency(CreateOrderHandler),
    ):
        command = CreateOrderCommand(...)
        return await handler.execute(command)
    ```

Performance Monitoring:
    Enable DEBUG logging to see handler creation times:
    ```python
    import logging
    logging.getLogger('bento.interfaces.fastapi.dependencies').setLevel(logging.DEBUG)
    ```
"""

from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Annotated, Any, Callable, Protocol, TypeVar
import time
import logging

from bento.application.ports.uow import UnitOfWork

if TYPE_CHECKING:
    from fastapi import Request


logger = logging.getLogger(__name__)

THandler = TypeVar("THandler")

# Cache for handler signature inspection (避免每次请求都执行反射)
_handler_signature_cache: dict[type, set[str]] = {}

# Flag to track if modules have been scanned (避免每次请求都扫描模块)
_modules_scanned: bool = False


def _get_handler_params(handler_cls: type) -> set[str]:
    """Get handler constructor parameters with caching.

    Uses reflection to inspect handler __init__ signature, but caches
    the result to avoid repeated reflection overhead.

    Args:
        handler_cls: Handler class to inspect

    Returns:
        Set of parameter names in the constructor
    """
    if handler_cls not in _handler_signature_cache:
        import inspect
        sig = inspect.signature(handler_cls.__init__)
        _handler_signature_cache[handler_cls] = set(sig.parameters.keys())
    return _handler_signature_cache[handler_cls]


def _create_handler_with_dependencies(
    handler_cls: type[THandler],
    uow: UnitOfWork,
    request: "Request",
) -> THandler:
    """Create handler instance with automatic dependency injection.

    Automatically detects if handler needs observability parameter
    and injects it from runtime.container, falling back to NoOp if unavailable.

    Performance: Uses cached reflection results to minimize overhead.

    Note: This function uses runtime reflection to determine the correct
    constructor signature. The type checker cannot verify this at compile time,
    but it is guaranteed to be correct at runtime.

    Args:
        handler_cls: Handler class to instantiate
        uow: UnitOfWork instance
        request: FastAPI Request (used to access runtime)

    Returns:
        Instantiated handler with all dependencies injected
    """
    start_time = time.perf_counter()

    params = _get_handler_params(handler_cls)

    if 'observability' in params:
        # Get observability from runtime
        runtime = getattr(request.app.state, 'bento_runtime', None)
        if runtime:
            try:
                observability = runtime.container.get('observability')
                handler = handler_cls(uow, observability)  # type: ignore[call-arg]

                elapsed = (time.perf_counter() - start_time) * 1000
                logger.debug(
                    f"Created Observable Handler {handler_cls.__name__} in {elapsed:.2f}ms"
                )
                return handler
            except (KeyError, AttributeError):
                pass

        # Fallback to NoOp if not available
        from bento.adapters.observability.noop import NoOpObservabilityProvider
        handler = handler_cls(uow, NoOpObservabilityProvider())  # type: ignore[call-arg]

        elapsed = (time.perf_counter() - start_time) * 1000
        logger.debug(
            f"Created Observable Handler {handler_cls.__name__} with NoOp in {elapsed:.2f}ms"
        )
        return handler
    else:
        # Standard handler with only uow
        handler = handler_cls(uow)  # type: ignore[call-arg]

        elapsed = (time.perf_counter() - start_time) * 1000
        logger.debug(
            f"Created Standard Handler {handler_cls.__name__} in {elapsed:.2f}ms"
        )
        return handler


class HandlerProtocol(Protocol):
    """Protocol for Handler classes.

    Supports both standard handlers (UoW only) and observable handlers (UoW + ObservabilityProvider).

    Note: The __init__ signature is intentionally not defined here because handlers
    can have different constructor signatures (with or without observability parameter).
    Runtime reflection in _create_handler_with_dependencies() ensures the correct
    constructor is called.
    """

    async def execute(self, command_or_query: Any) -> Any: ...


def create_handler_dependency(get_uow_dependency: Callable[..., Any]) -> Callable[[type[Any]], Any]:
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
    except ImportError as e:
        raise ImportError(
            "FastAPI is required for create_handler_dependency. "
            "Install it with: pip install fastapi"
        ) from e

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
            return _create_handler_with_dependencies(handler_cls, uow, request)

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
    except ImportError as e:
        raise ImportError(
            "FastAPI is required for handler_dependency. "
            "Install it with: pip install fastapi"
        ) from e

    async def factory(request: Request):
        """Create handler with UoW from runtime."""
        runtime = request.app.state.runtime

        # Ensure modules are scanned (triggers @repository_for decorators)
        # Only scan once to avoid repeated overhead
        global _modules_scanned
        if not _modules_scanned:
            import importlib
            scan_start = time.perf_counter()

            for module in runtime.registry.resolve_order():
                for pkg in module.scan_packages:
                    try:
                        importlib.import_module(pkg)
                    except ImportError:
                        pass

            scan_elapsed = (time.perf_counter() - scan_start) * 1000
            logger.info(f"Module scanning completed in {scan_elapsed:.2f}ms")
            _modules_scanned = True

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

            # Create handler with automatic dependency injection
            yield _create_handler_with_dependencies(handler_cls, uow, request)

    return Depends(factory)
