"""Repository Registry - Automatic discovery of Repository implementations.

This module provides the @repository_for decorator for automatic repository
registration, eliminating the need for manual registration in dependencies.py.

Example:
    ```python
    from bento.infrastructure.repository import repository_for

    @repository_for(Product)
    class ProductRepository(RepositoryAdapter[Product, ProductPO, ID]):
        pass

    # UoW automatically has access to ProductRepository
    repo = uow.repository(Product)  # Works without manual registration
    ```
"""

from collections.abc import Callable
from typing import Any, TypeVar

from bento.domain.aggregate import AggregateRoot

AR = TypeVar("AR", bound=AggregateRoot)

# Global registry: AggregateRoot type -> Repository class
_repository_registry: dict[type[AggregateRoot], type[Any]] = {}


def repository_for[AR: AggregateRoot](aggregate_type: type[AR]) -> Callable[[type], type]:
    """Decorator to register a Repository for a specific AggregateRoot.

    This decorator registers the repository class in a global registry,
    allowing the UnitOfWork to automatically discover and use it.

    Args:
        aggregate_type: The AggregateRoot class this repository serves

    Returns:
        Decorator function

    Example:
        ```python
        @repository_for(Product)
        class ProductRepository(RepositoryAdapter[Product, ProductPO, ID]):
            pass

        @repository_for(Category)
        class CategoryRepository(RepositoryAdapter[Category, CategoryPO, ID]):
            pass
        ```
    """
    def decorator(cls: type) -> type:
        _repository_registry[aggregate_type] = cls
        return cls
    return decorator


def get_repository_registry() -> dict[type[AggregateRoot], type[Any]]:
    """Get a copy of the repository registry.

    Returns:
        Dictionary mapping AggregateRoot types to Repository classes
    """
    return _repository_registry.copy()


def get_repository_class[AR: AggregateRoot](aggregate_type: type[AR]) -> type[Any] | None:
    """Get the repository class for a specific aggregate type.

    Args:
        aggregate_type: The AggregateRoot class

    Returns:
        Repository class if registered, None otherwise
    """
    return _repository_registry.get(aggregate_type)


def clear_registry() -> None:
    """Clear the repository registry. Useful for testing."""
    _repository_registry.clear()
