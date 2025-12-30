"""Port registry for cross-BC services."""

import logging
from collections.abc import Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class PortRegistry:
    """Registry for outbound port adapters."""

    def __init__(self) -> None:
        self._factories: dict[type, Callable[[AsyncSession], Any]] = {}

    def register(
        self,
        port_type: type,
        factory: Callable[[AsyncSession], Any],
    ) -> "PortRegistry":
        """Register port adapter factory.

        Args:
            port_type: Port interface type (e.g., IProductCatalogService)
            factory: Function that creates adapter from session

        Returns:
            Self for chaining

        Example:
            ```python
            registry.register(
                IProductCatalogService,
                lambda s: ProductCatalogAdapter(s)
            )
            ```
        """
        self._factories[port_type] = factory
        logger.debug(f"Registered port adapter for {port_type.__name__}")
        return self

    def get_factory(self, port_type: type) -> Callable:
        """Get port adapter factory.

        Args:
            port_type: Port interface type

        Returns:
            Adapter factory function

        Raises:
            ValueError: If no adapter registered for the port type
        """
        if port_type not in self._factories:
            raise ValueError(
                f"No adapter registered for port {port_type.__name__}. "
                f"Available: {[t.__name__ for t in self._factories.keys()]}"
            )
        return self._factories[port_type]
