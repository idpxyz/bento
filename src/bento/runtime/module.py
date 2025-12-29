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

        def get_routers(self):
            return [(catalog_router, "/api/v1/catalog")]  # With prefix
    ```
"""

from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, Sequence, Union

if TYPE_CHECKING:
    from fastapi import APIRouter
    from starlette.middleware import Middleware

    from bento.runtime.container import BentoContainer

# Router can be plain APIRouter or (APIRouter, prefix) tuple
RouterSpec = Union["APIRouter", tuple["APIRouter", str]]


class BentoModule(ABC):
    """Base class for application modules.

    Modules are the building blocks of a Bento application.
    Each module can:
    - Declare dependencies on other modules
    - Register services in the container
    - Define startup/shutdown hooks
    - Provide FastAPI routers (with optional prefixes)
    - Provide middleware
    - Declare packages to scan for @repository_for decorators
    - Declare database requirements

    Attributes:
        name: Unique module name
        requires: List of module names this module depends on
        scan_packages: List of package names to scan for decorators
        requires_database: If True, this module requires database to be configured
    """

    name: str = ""
    requires: Sequence[str] = ()
    scan_packages: Sequence[str] = ()
    requires_database: bool = False

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

    def get_routers(self) -> list[RouterSpec]:
        """Return FastAPI routers provided by this module.

        Override to provide API routers. Can return:
        - Plain APIRouter: app.include_router(router)
        - Tuple (router, prefix): app.include_router(router, prefix=prefix)

        Returns:
            List of routers or (router, prefix) tuples

        Example:
            ```python
            def get_routers(self):
                return [
                    (products_router, "/api/v1/products"),
                    (categories_router, "/api/v1/categories"),
                ]
            ```
        """
        return []

    def get_middleware(self) -> list["Middleware"]:
        """Return middleware provided by this module.

        Override to provide Starlette middleware.

        Returns:
            List of Middleware instances

        Example:
            ```python
            from starlette.middleware import Middleware
            from starlette.middleware.cors import CORSMiddleware

            def get_middleware(self):
                return [
                    Middleware(CORSMiddleware, allow_origins=["*"]),
                ]
            ```
        """
        return []
