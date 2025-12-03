"""Application Layer Decorators for CQRS Handlers.

This module provides decorators to simplify handler registration and dependency injection.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from bento.application.cqrs.command_handler import CommandHandler
    from bento.application.cqrs.query_handler import QueryHandler

# Type variables
THandler = TypeVar("THandler")
TCommandHandler = TypeVar("TCommandHandler", bound="CommandHandler[Any, Any]")
TQueryHandler = TypeVar("TQueryHandler", bound="QueryHandler[Any, Any]")


# Global registry for handlers (for DI frameworks)
_COMMAND_HANDLERS: dict[str, type] = {}
_QUERY_HANDLERS: dict[str, type] = {}


def command_handler[TCommandHandler: "CommandHandler[Any, Any]"](
    cls: type[TCommandHandler],
) -> type[TCommandHandler]:
    """Decorator for Command Handlers.

    Marks a class as a Command Handler and registers it for dependency injection.

    Features:
    - Automatic registration in DI container
    - Metadata tagging (handler_type = "command")
    - Validation of CommandHandler inheritance

    Example:
        ```python
        @command_handler
        class CreateProductHandler(CommandHandler[CreateProductCommand, str]):
            async def handle(self, command):
                ...

        # In FastAPI route
        @router.post("/products")
        async def create_product(
            handler: Annotated[CreateProductHandler, Depends(get_handler)],
        ):
            result = await handler.execute(command)
        ```

    Args:
        cls: The handler class to decorate

    Returns:
        The decorated class with metadata

    Raises:
        TypeError: If class doesn't inherit from CommandHandler
    """
    # Validate inheritance
    from bento.application.cqrs.command_handler import CommandHandler

    if not issubclass(cls, CommandHandler):
        msg = f"{cls.__name__} must inherit from CommandHandler"
        raise TypeError(msg)

    # Add metadata
    cls.__handler_type__ = "command"  # type: ignore[attr-defined]
    cls.__is_handler__ = True  # type: ignore[attr-defined]

    # Register in global registry
    handler_name = cls.__name__
    _COMMAND_HANDLERS[handler_name] = cls

    return cls


def query_handler[TQueryHandler: "QueryHandler[Any, Any]"](
    cls: type[TQueryHandler],
) -> type[TQueryHandler]:
    """Decorator for Query Handlers.

    Marks a class as a Query Handler and registers it for dependency injection.

    Features:
    - Automatic registration in DI container
    - Metadata tagging (handler_type = "query")
    - Validation of QueryHandler inheritance

    Example:
        ```python
        @query_handler
        class GetProductHandler(QueryHandler[GetProductQuery, ProductDTO]):
            async def handle(self, query):
                ...

        # In FastAPI route
        @router.get("/products/{id}")
        async def get_product(
            handler: Annotated[GetProductHandler, Depends(get_handler)],
        ):
            result = await handler.execute(query)
        ```

    Args:
        cls: The handler class to decorate

    Returns:
        The decorated class with metadata

    Raises:
        TypeError: If class doesn't inherit from QueryHandler
    """
    # Validate inheritance
    from bento.application.cqrs.query_handler import QueryHandler

    if not issubclass(cls, QueryHandler):
        msg = f"{cls.__name__} must inherit from QueryHandler"
        raise TypeError(msg)

    # Add metadata
    cls.__handler_type__ = "query"  # type: ignore[attr-defined]
    cls.__is_handler__ = True  # type: ignore[attr-defined]

    # Register in global registry
    handler_name = cls.__name__
    _QUERY_HANDLERS[handler_name] = cls

    return cls


def get_registered_handlers() -> dict[str, dict[str, type]]:
    """Get all registered handlers.

    Returns:
        Dictionary with 'commands' and 'queries' handler registries

    Example:
        ```python
        handlers = get_registered_handlers()
        print(handlers["commands"])  # All command handlers
        print(handlers["queries"])   # All query handlers
        ```
    """
    return {"commands": _COMMAND_HANDLERS.copy(), "queries": _QUERY_HANDLERS.copy()}


def is_handler(cls: type) -> bool:
    """Check if a class is a registered handler.

    Args:
        cls: Class to check

    Returns:
        True if class is decorated with @command_handler or @query_handler
    """
    return getattr(cls, "__is_handler__", False)


def get_handler_type(cls: type) -> str | None:
    """Get the handler type of a class.

    Args:
        cls: Handler class

    Returns:
        "command", "query", or None if not a handler
    """
    return getattr(cls, "__handler_type__", None)


# Helper for FastAPI dependency injection
def create_handler_factory[THandler](handler_cls: type[THandler]) -> Callable[..., THandler]:
    """Create a factory function for dependency injection.

    This is a helper to integrate with FastAPI's Depends().

    Example:
        ```python
        @command_handler
        class CreateProductHandler(CommandHandler[...]):
            ...

        # Create factory
        get_create_product_handler = create_handler_factory(CreateProductHandler)

        # Use in route
        @router.post("/")
        async def create_product(
            handler: Annotated[CreateProductHandler, Depends(get_create_product_handler)],
        ):
            ...
        ```

    Args:
        handler_cls: The handler class

    Returns:
        Factory function that creates handler instances
    """

    def factory(*args: Any, **kwargs: Any) -> THandler:
        """Factory function to create handler instance."""
        return handler_cls(*args, **kwargs)

    # Copy metadata from the class (optional)
    factory.__name__ = f"get_{handler_cls.__name__}"
    factory.__doc__ = f"Factory for {handler_cls.__name__}"

    return factory
