"""Bento Runtime Bootstrap.

Provides the main entry point for bootstrapping a Bento application
with module registration, contract validation, and lifecycle management.

Example:
    ```python
    from bento.runtime import BentoRuntime

    runtime = (
        RuntimeBuilder()
        .with_modules(InfraModule(), CatalogModule(), OrderingModule())
        .build_runtime()
    )

    app = runtime.create_fastapi_app(title="My Shop")
    ```
"""

from __future__ import annotations

import asyncio
import importlib
import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from bento.runtime.config import RuntimeConfig
from bento.runtime.container.base import BentoContainer
from bento.runtime.database import DatabaseManager
from bento.runtime.integrations.di import DIIntegration
from bento.runtime.integrations.fastapi import FastAPIIntegration
from bento.runtime.integrations.modules import ModuleManager
from bento.runtime.integrations.performance import PerformanceMonitor
from bento.runtime.lifecycle import startup as lifecycle_startup
from bento.runtime.lifecycle.manager import LifecycleManager
from bento.runtime.ports import PortRegistry
from bento.runtime.registry import ModuleRegistry
from bento.runtime.repository import RepositoryRegistry

if TYPE_CHECKING:
    from fastapi import FastAPI

    from bento.runtime.module import BentoModule

logger = logging.getLogger(__name__)


@dataclass
class BentoRuntime:
    """Main runtime orchestrator for Bento applications.

    Combines module registry, DI container, contract validation,
    and FastAPI integration into a unified bootstrap experience.

    Example:
        ```python
        runtime = (
            RuntimeBuilder()
            .with_modules(InfraModule(), CatalogModule(), OrderingModule())
            .build_runtime()
        )

        app = runtime.create_fastapi_app(title="My Shop API")
        ```
    """

    config: RuntimeConfig = field(default_factory=RuntimeConfig)
    container: BentoContainer = field(default_factory=BentoContainer)
    registry: ModuleRegistry = field(default_factory=ModuleRegistry)
    repository_registry: RepositoryRegistry = field(default_factory=RepositoryRegistry)
    port_registry: PortRegistry = field(default_factory=PortRegistry)
    _built: bool = field(default=False, repr=False)
    _contracts: Any = field(default=None, repr=False)
    _session_factory: Any = field(default=None, repr=False)
    _get_uow_func: Any = field(default=None, repr=False)
    _handler_dependency_func: Any = field(default=None, repr=False)
    _uow_factory: Any = field(default=None, repr=False)
    _event_bus: Any = field(default=None, repr=False)
    _startup_metrics: dict[str, float] = field(default_factory=dict, repr=False)

    # Integration managers (initialized in __post_init__)
    _lifecycle_manager: LifecycleManager = field(init=False, repr=False)
    _fastapi_integration: FastAPIIntegration = field(init=False, repr=False)
    _performance_monitor: PerformanceMonitor = field(init=False, repr=False)
    _module_manager: ModuleManager = field(init=False, repr=False)
    _di_integration: DIIntegration = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize all integration managers after dataclass init."""
        object.__setattr__(self, "_lifecycle_manager", LifecycleManager(self))
        object.__setattr__(self, "_fastapi_integration", FastAPIIntegration(self))
        object.__setattr__(self, "_performance_monitor", PerformanceMonitor(self))
        object.__setattr__(self, "_module_manager", ModuleManager(self))
        object.__setattr__(self, "_di_integration", DIIntegration(self))

    def _scan_module_packages(self, module: BentoModule) -> None:
        """Scan module packages for decorator registrations.

        This imports all packages listed in module.scan_packages to trigger
        decorator registrations (like @repository_for) and auto-discovers
        repositories.

        Args:
            module: Module to scan
        """
        if not module.scan_packages:
            return

        logger.debug(f"Scanning packages for module {module.name}: {module.scan_packages}")

        # Auto-discover repositories
        self.repository_registry.auto_discover(list(module.scan_packages))

        for package_name in module.scan_packages:
            try:
                importlib.import_module(package_name)
                logger.debug(f"Imported package: {package_name}")
            except Exception as e:
                error_msg = (
                    f"Failed to import package {package_name} for module {module.name}: {e}\n"
                    f"This may cause Repository decorators (@repository_for) to not be registered.\n"
                    f"Ensure the package exists and is properly installed."
                )

                if self.config.environment != "local":
                    raise RuntimeError(error_msg) from e

                logger.warning(error_msg)

    async def build_async(self) -> BentoRuntime:
        """Build the runtime (async version).

        Runs gates and registers all modules.

        Returns:
            Self for chaining
        """
        if self._built:
            logger.debug("Runtime already built, skipping")
            return self

        start_time = time.time()

        logger.info(
            f"Building runtime: {self.config.service_name} "
            f"(env={self.config.environment})"
        )

        # Store config in container
        self.container.set("config", self.config)

        # Run startup phases via lifecycle startup module
        gate_start = time.time()
        await lifecycle_startup.run_gates(self)
        gate_elapsed = time.time() - gate_start
        logger.debug(f"Gates validation completed in {gate_elapsed:.3f}s")

        register_start = time.time()
        await lifecycle_startup.register_modules(self)
        register_elapsed = time.time() - register_start
        logger.debug(f"Module registration completed in {register_elapsed:.3f}s")

        db_start = time.time()
        self._setup_database()
        db_elapsed = time.time() - db_start
        logger.debug(f"Database setup completed in {db_elapsed:.3f}s")

        self._built = True

        total_elapsed = time.time() - start_time

        # Store startup metrics for performance monitoring
        self._startup_metrics = {
            "total_time": total_elapsed,
            "gates_time": gate_elapsed,
            "register_time": register_elapsed,
            "database_time": db_elapsed,
        }

        logger.info(
            f"Runtime built successfully in {total_elapsed:.2f}s "
            f"with {len(self.registry)} modules: {self.registry.names()}"
        )

        return self

    def build(self) -> BentoRuntime:
        """Build the runtime (sync wrapper).

        For async applications, prefer build_async().

        Returns:
            Self for chaining
        """
        try:
            asyncio.get_running_loop()
            raise RuntimeError(
                "Cannot use build() in async context. Use 'await runtime.build_async()'"
            )
        except RuntimeError as e:
            if "Cannot use build()" in str(e):
                raise
            asyncio.run(self.build_async())

        return self

    def create_fastapi_app(
        self,
        title: str = "Bento API",
        description: str = "",
        version: str = "1.0.0",
        docs_url: str = "/docs",
        **fastapi_kwargs: Any,
    ) -> FastAPI:
        """Create a FastAPI application with lifespan management.

        Args:
            title: API title
            description: API description
            version: API version
            docs_url: Swagger docs URL
            **fastapi_kwargs: Additional FastAPI arguments

        Returns:
            Configured FastAPI application
        """
        return self._fastapi_integration.create_app(
            title=title,
            description=description,
            version=version,
            docs_url=docs_url,
            **fastapi_kwargs,
        )

    def _setup_database(self) -> None:
        """Setup database session factory using DatabaseManager.

        Raises:
            RuntimeError: If database is required but not configured
        """
        db_manager = DatabaseManager(self)
        db_manager.setup()

    # Performance monitoring delegation
    def get_startup_metrics(self) -> dict[str, float]:
        """Get startup performance metrics."""
        return self._performance_monitor.get_metrics()

    def log_startup_metrics(self) -> None:
        """Log startup performance metrics to logger."""
        self._performance_monitor.log_metrics()

    # Module management delegation
    async def reload_module(self, name: str) -> BentoRuntime:
        """Reload a module at runtime (hot reload)."""
        return await self._module_manager.reload(name)

    async def unload_module(self, name: str) -> BentoRuntime:
        """Unload a module at runtime."""
        return await self._module_manager.unload(name)

    async def load_module(self, module: BentoModule) -> BentoRuntime:
        """Load a module at runtime."""
        return await self._module_manager.load(module)

    # Dependency injection delegation
    @property
    def get_uow(self):
        """Get the UnitOfWork dependency function for FastAPI."""
        return self._di_integration.get_uow()

    @property
    def handler_dependency(self):
        """Get the handler dependency function for FastAPI."""
        return self._di_integration.get_handler_dependency()

    # Test support methods
    def with_test_mode(self, enabled: bool = True) -> BentoRuntime:
        """Enable test mode for the runtime.

        Args:
            enabled: Whether to enable test mode (default: True)

        Returns:
            Self for chaining
        """
        self.config.test_mode = enabled
        logger.debug(f"Test mode: {enabled}")
        return self

    def with_mock_module(
        self,
        name: str,
        services: dict[str, Any] | None = None,
        on_register_fn: Any = None,
    ) -> BentoRuntime:
        """Register a mock module for testing.

        Args:
            name: Module name
            services: Dictionary of services to register
            on_register_fn: Optional async function to call on registration

        Returns:
            Self for chaining
        """
        from bento.runtime.module import BentoModule

        class MockModule(BentoModule):
            pass

        mock = MockModule()
        mock.name = name

        async def on_register(container):
            if services:
                for key, value in services.items():
                    container.set(key, value)
            if on_register_fn:
                await on_register_fn(container)

        mock.on_register = on_register

        self.registry.register(mock)
        logger.debug(f"Mock module registered: {name}")
        return self


    # Module assertion methods
    def assert_module_loaded(self, name: str) -> bool:
        """Assert that a module is loaded.

        Args:
            name: Module name

        Returns:
            True if module is loaded

        Raises:
            AssertionError: If module is not loaded
        """
        if not self.registry.has(name):
            raise AssertionError(f"Module not loaded: {name}")
        return True

    def assert_service_registered(self, key: str) -> bool:
        """Assert that a service is registered in the container.

        Args:
            key: Service key

        Returns:
            True if service is registered

        Raises:
            AssertionError: If service is not registered
        """
        if not self.container.has(key):
            raise AssertionError(f"Service not registered: {key}")
        return True
