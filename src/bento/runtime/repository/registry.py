"""Repository registry with auto-discovery."""

from __future__ import annotations

import importlib
import inspect
import logging
from collections.abc import Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class RepositoryRegistry:
    """Registry for repository factories with auto-discovery support."""

    def __init__(self) -> None:
        self._factories: dict[type, Callable[[AsyncSession], Any]] = {}

    def register(
        self,
        aggregate_type: type,
        factory: Callable[[AsyncSession], Any],
    ) -> RepositoryRegistry:
        """Register repository factory for an aggregate type.

        Args:
            aggregate_type: Aggregate root class
            factory: Function that creates repository from session

        Returns:
            Self for chaining

        Example:
            ```python
            registry.register(Order, lambda s: OrderRepository(s))
            ```
        """
        self._factories[aggregate_type] = factory
        logger.debug(f"Registered repository for {aggregate_type.__name__}")
        return self

    def get_factory(self, aggregate_type: type) -> Callable:
        """Get repository factory for an aggregate type.

        Args:
            aggregate_type: Aggregate root class

        Returns:
            Repository factory function

        Raises:
            ValueError: If no repository registered for the aggregate type
        """
        if aggregate_type not in self._factories:
            raise ValueError(
                f"No repository registered for {aggregate_type.__name__}. "
                f"Available: {[t.__name__ for t in self._factories.keys()]}"
            )
        return self._factories[aggregate_type]

    def auto_discover(self, packages: list[str]) -> None:
        """Auto-discover repositories using @repository_for decorator.

        Scans packages for classes decorated with @repository_for and
        automatically registers them.

        Args:
            packages: List of package names to scan

        Example:
            ```python
            registry.auto_discover(["contexts.ordering.infrastructure"])
            ```
        """
        for package_name in packages:
            try:
                module = importlib.import_module(package_name)
                self._scan_module(module)
            except Exception as e:
                logger.warning(f"Failed to scan package {package_name}: {e}")

    def _scan_module(self, module: Any) -> None:
        """Scan module for repository classes."""
        for _, obj in inspect.getmembers(module):
            if inspect.isclass(obj):
                # Check for @repository_for decorator metadata
                if hasattr(obj, "__aggregate_type__"):
                    aggregate_type = obj.__aggregate_type__

                    # Create factory that instantiates the repository
                    def factory(s, cls=obj):
                        return cls(s)

                    self.register(aggregate_type, factory)
                    logger.info(
                        f"Auto-discovered repository: {obj.__name__} for {aggregate_type.__name__}"
                    )
