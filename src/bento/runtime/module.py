"""Bento Module System.

This module provides the base class for defining application modules
with dependency management and lifecycle hooks.

Example:
    ```python
    from bento.runtime import BentoModule

    class CatalogModule(BentoModule):
        name = "catalog"
        requires = ["infra"]

        async def on_register(self, container):
            container.set("catalog.repository", CategoryRepository)

        async def on_startup(self, container):
            # Warmup cache, etc.
            pass

        async def on_shutdown(self, container):
            # Cleanup
            pass
    ```
"""

from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:
    from fastapi import APIRouter

    from bento.runtime.container import BentoContainer


class BentoModule(ABC):
    """Base class for application modules.

    Modules are the building blocks of a Bento application.
    Each module can:
    - Declare dependencies on other modules
    - Register services in the container
    - Define startup/shutdown hooks
    - Provide FastAPI routers

    Attributes:
        name: Unique module name
        requires: List of module names this module depends on
    """

    name: str = ""
    requires: Sequence[str] = ()

    def __init__(self) -> None:
        if not self.name:
            self.name = self.__class__.__name__.lower().replace("module", "")

    async def on_register(self, container: "BentoContainer") -> None:
        """Called when module is registered.

        Override to register services, repositories, handlers in container.

        Args:
            container: The DI container
        """
        pass

    async def on_startup(self, container: "BentoContainer") -> None:
        """Called during application startup.

        Override for initialization: cache warmup, connections, etc.

        Args:
            container: The DI container
        """
        pass

    async def on_shutdown(self, container: "BentoContainer") -> None:
        """Called during application shutdown.

        Override for cleanup: close connections, flush buffers, etc.

        Args:
            container: The DI container
        """
        pass

    def get_routers(self) -> list[APIRouter]:
        """Return FastAPI routers provided by this module.

        Override to provide API routers.

        Returns:
            List of FastAPI APIRouter instances
        """
        return []
