"""Port Registry - Automatic discovery of Port implementations.

This module provides the @port_for decorator for automatic port adapter
registration, eliminating the need for manual registration.

Example:
    ```python
    from bento.infrastructure.ports import port_for

    @port_for(IProductCatalogService)
    class ProductCatalogAdapter:
        def __init__(self, session):
            self.session = session

    # UoW automatically has access to the adapter
    adapter = uow.port(IProductCatalogService)
    ```
"""

from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")

# Global registry: Port interface -> Adapter factory
_port_registry: dict[type, type[Any]] = {}


def port_for[T](port_interface: type[T]) -> Callable[[type], type]:
    """Decorator to register an Adapter for a specific Port interface.

    This decorator registers the adapter class in a global registry,
    allowing the UnitOfWork to automatically discover and use it.

    Args:
        port_interface: The Port interface (Protocol) this adapter implements

    Returns:
        Decorator function

    Example:
        ```python
        @port_for(IProductCatalogService)
        class ProductCatalogAdapter:
            def __init__(self, session):
                self.session = session
        ```
    """
    def decorator(cls: type) -> type:
        _port_registry[port_interface] = cls
        return cls
    return decorator


def get_port_registry() -> dict[type, type[Any]]:
    """Get a copy of the port registry.

    Returns:
        Dictionary mapping Port interfaces to Adapter classes
    """
    return _port_registry.copy()


def get_port_adapter[T](port_interface: type[T]) -> type[Any] | None:
    """Get the adapter class for a specific port interface.

    Args:
        port_interface: The Port interface

    Returns:
        Adapter class if registered, None otherwise
    """
    return _port_registry.get(port_interface)


def clear_port_registry() -> None:
    """Clear the port registry. Useful for testing."""
    _port_registry.clear()
