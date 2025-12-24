"""FastAPI Dependency Injection utilities for Bento Framework.

This module provides dependency injection helpers for integrating Bento's
CQRS handlers with FastAPI routes.

Example:
    ```python
    from bento.interfaces.fastapi import create_handler_dependency

    # Create handler_dependency with your get_uow
    handler_dependency = create_handler_dependency(get_uow)

    @router.post("/orders")
    async def create_order(
        request: CreateOrderRequest,
        handler: Annotated[CreateOrderHandler, handler_dependency(CreateOrderHandler)],
    ):
        command = CreateOrderCommand(...)
        return await handler.execute(command)
    ```
"""

from typing import Annotated, Any, Callable, Protocol, TypeVar

from bento.application.ports.uow import UnitOfWork


class HandlerProtocol(Protocol):
    """Protocol for Handler classes that accept UoW in constructor.

    All CommandHandler and QueryHandler classes follow this protocol.
    """

    def __init__(self, uow: UnitOfWork) -> None: ...


THandler = TypeVar("THandler", bound=HandlerProtocol)


def create_handler_dependency(get_uow_dependency: Callable[..., Any]) -> Callable[[type[THandler]], Any]:
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

    def handler_dependency(handler_cls: type[THandler]) -> Any:
        """Create a FastAPI dependency for a specific Handler class.

        Args:
            handler_cls: The Handler class to instantiate

        Returns:
            A FastAPI Depends instance
        """
        def factory(uow: Annotated[UnitOfWork, Depends(get_uow_dependency)]) -> THandler:
            return handler_cls(uow)
        return Depends(factory)

    return handler_dependency
