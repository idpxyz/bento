"""Container scope for managing scoped service instances.

Provides scope-based service lifetime management.
"""

from typing import Any


class ContainerScope:
    """Scoped container for managing scoped service instances.

    Each scope maintains its own instances of scoped services.
    """

    def __init__(self) -> None:
        """Initialize a new container scope."""
        self._scoped_services: dict[str, Any] = {}

    def set(self, key: str, value: Any) -> None:
        """Register a scoped service instance.

        Args:
            key: Service identifier
            value: Service instance
        """
        self._scoped_services[key] = value

    def get(self, key: str) -> Any | None:
        """Retrieve a scoped service instance.

        Args:
            key: Service identifier

        Returns:
            Service instance or None if not found
        """
        return self._scoped_services.get(key)

    def has(self, key: str) -> bool:
        """Check if scoped service is registered.

        Args:
            key: Service identifier

        Returns:
            True if registered
        """
        return key in self._scoped_services

    def clear(self) -> None:
        """Clear all scoped service instances."""
        self._scoped_services.clear()
