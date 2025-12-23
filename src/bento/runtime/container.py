"""Bento DI Container.

A simple dependency injection container for managing application services.

Example:
    ```python
    from bento.runtime import BentoContainer

    container = BentoContainer()
    container.set("db.session_factory", session_factory)
    container.set("cache", redis_cache)

    # Retrieve
    cache = container.get("cache")
    ```
"""

from __future__ import annotations

from typing import Any, TypeVar, overload

T = TypeVar("T")


class BentoContainer:
    """Simple dependency injection container.

    Provides service registration and retrieval with optional type hints.
    Thread-safe for read operations after initial registration.
    """

    def __init__(self) -> None:
        self._services: dict[str, Any] = {}
        self._factories: dict[str, Any] = {}

    def set(self, key: str, value: Any) -> None:
        """Register a service instance.

        Args:
            key: Service identifier
            value: Service instance or value
        """
        self._services[key] = value

    def set_factory(self, key: str, factory: Any) -> None:
        """Register a service factory (lazy instantiation).

        Args:
            key: Service identifier
            factory: Callable that creates the service
        """
        self._factories[key] = factory

    @overload
    def get(self, key: str) -> Any: ...

    @overload
    def get(self, key: str, default: T) -> T: ...

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a service by key.

        Args:
            key: Service identifier
            default: Default value if not found

        Returns:
            Service instance or default
        """
        if key in self._services:
            return self._services[key]

        if key in self._factories:
            # Lazy instantiation
            self._services[key] = self._factories[key]()
            return self._services[key]

        if default is not None:
            return default

        raise KeyError(f"Service not found: {key}")

    def has(self, key: str) -> bool:
        """Check if service is registered.

        Args:
            key: Service identifier

        Returns:
            True if registered
        """
        return key in self._services or key in self._factories

    def keys(self) -> list[str]:
        """Return all registered service keys."""
        return list(set(self._services.keys()) | set(self._factories.keys()))

    def clear(self) -> None:
        """Clear all registered services."""
        self._services.clear()
        self._factories.clear()
