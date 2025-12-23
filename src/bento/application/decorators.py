"""Application Layer Decorators for CQRS Handlers.

This module provides decorators to simplify handler registration and dependency injection.

Includes:
- @command_handler: Register command handlers
- @query_handler: Register query handlers
- @state_transition: Validate state machine transitions (Contract-as-Code)
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from bento.application.cqrs.command_handler import CommandHandler
    from bento.application.cqrs.query_handler import QueryHandler
    from bento.contracts import Contracts

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


# =============================================================================
# State Transition Decorator (Contract-as-Code)
# =============================================================================

# Global contracts reference (set during app startup)
_global_contracts: "Contracts | None" = None


def set_global_contracts(contracts: "Contracts") -> None:
    """Set the global contracts instance.

    Called during application startup after loading contracts.

    Args:
        contracts: Loaded Contracts instance
    """
    global _global_contracts
    _global_contracts = contracts


def get_global_contracts() -> "Contracts | None":
    """Get the global contracts instance."""
    return _global_contracts


def state_transition(
    aggregate: str,
    command: str,
    state_field: str = "status",
) -> Callable[[type[TCommandHandler]], type[TCommandHandler]]:
    """Decorator to validate state machine transitions before command execution.

    This decorator integrates Contract-as-Code state machines with CommandHandlers.
    Before the command is executed, it validates that the transition is allowed
    based on the aggregate's current state.

    Args:
        aggregate: Name of the aggregate (must match state machine definition)
        command: Command name (must match transition command in state machine)
        state_field: Field name on the aggregate that holds the current state

    Example:
        ```python
        @state_transition(aggregate="Order", command="Submit")
        @command_handler
        class SubmitOrderHandler(CommandHandler[SubmitOrderCommand, Order]):
            async def handle(self, command: SubmitOrderCommand) -> Order:
                order = await self.uow.repository(Order).get(command.order_id)
                order.submit()
                await self.uow.repository(Order).save(order)
                return order
        ```

    The decorator will:
    1. Load the aggregate from the repository
    2. Get the current state from the state_field
    3. Validate the transition against the state machine
    4. Raise StateTransitionException if invalid

    Note:
        The command class must have an 'aggregate_id' or '{aggregate_name}_id' field
        to identify which aggregate to load for validation.
    """

    def decorator(cls: type[TCommandHandler]) -> type[TCommandHandler]:
        # Store metadata on the class
        cls.__state_transition__ = {  # type: ignore[attr-defined]
            "aggregate": aggregate,
            "command": command,
            "state_field": state_field,
        }

        # Wrap the handle method
        original_handle = cls.handle

        @functools.wraps(original_handle)
        async def wrapped_handle(self: Any, cmd: Any) -> Any:
            # Get contracts
            contracts = _global_contracts
            if contracts is None:
                # No contracts loaded, skip validation
                return await original_handle(self, cmd)

            # Try to get aggregate ID from command
            aggregate_id = _extract_aggregate_id(cmd, aggregate)
            if aggregate_id is None:
                # Can't determine aggregate ID, skip validation
                return await original_handle(self, cmd)

            # Load aggregate to get current state
            try:
                aggregate_cls = _get_aggregate_class(self, aggregate)
                if aggregate_cls is None:
                    return await original_handle(self, cmd)

                repo = self.uow.repository(aggregate_cls)
                agg = await repo.get(aggregate_id)

                if agg is None:
                    # Aggregate not found, let handler deal with it
                    return await original_handle(self, cmd)

                # Get current state
                current_state = getattr(agg, state_field, None)
                if current_state is None:
                    return await original_handle(self, cmd)

                # Validate transition
                contracts.state_machines.validate(aggregate, current_state, command)

            except Exception as e:
                # Re-raise StateTransitionException, let others pass through
                from bento.contracts import StateTransitionException
                if isinstance(e, StateTransitionException):
                    raise
                # Other exceptions (e.g., aggregate not found) - continue to handler
                pass

            # Execute original handler
            return await original_handle(self, cmd)

        cls.handle = wrapped_handle  # type: ignore[method-assign]
        return cls

    return decorator


def _extract_aggregate_id(cmd: Any, aggregate: str) -> Any:
    """Extract aggregate ID from command object."""
    # Try common patterns
    patterns = [
        "aggregate_id",
        f"{aggregate.lower()}_id",
        "id",
        "entity_id",
    ]

    for pattern in patterns:
        if hasattr(cmd, pattern):
            return getattr(cmd, pattern)

    return None


def _get_aggregate_class(handler: Any, aggregate_name: str) -> type | None:
    """Get aggregate class from handler's module or registry."""
    # Try to find in handler's module
    import sys

    handler_module = sys.modules.get(handler.__class__.__module__)
    if handler_module:
        # Look for class with matching name
        for name in dir(handler_module):
            if name == aggregate_name:
                return getattr(handler_module, name)

    return None
