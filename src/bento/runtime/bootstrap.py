"""Bento Runtime Bootstrap.

Provides the main entry point for bootstrapping a Bento application
with module registration, contract validation, and lifecycle management.

Example:
    ```python
    from bento.runtime import BentoRuntime

    runtime = (
        BentoRuntime()
        .with_contracts("./contracts")
        .with_modules(InfraModule(), CatalogModule(), OrderingModule())
        .build()
    )

    app = runtime.create_fastapi_app(title="My Shop")
    ```
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bento.runtime.container import BentoContainer
from bento.runtime.registry import ModuleRegistry

if TYPE_CHECKING:
    from fastapi import FastAPI

    from bento.runtime.module import BentoModule

logger = logging.getLogger(__name__)


@dataclass
class RuntimeConfig:
    """Configuration for BentoRuntime."""

    contracts_path: str | None = None
    require_contracts: bool = False
    environment: str = "local"
    service_name: str = "bento-app"
    skip_gates_in_local: bool = True


@dataclass
class BentoRuntime:
    """Main runtime orchestrator for Bento applications.

    Combines module registry, DI container, contract validation,
    and FastAPI integration into a unified bootstrap experience.

    Example:
        ```python
        runtime = (
            BentoRuntime(service_name="my-shop")
            .with_contracts("./contracts")
            .with_modules(
                InfraModule(),
                CatalogModule(),
                OrderingModule(),
            )
            .build()
        )

        # Create FastAPI app
        app = runtime.create_fastapi_app(title="My Shop API")
        ```
    """

    config: RuntimeConfig = field(default_factory=RuntimeConfig)
    container: BentoContainer = field(default_factory=BentoContainer)
    registry: ModuleRegistry = field(default_factory=ModuleRegistry)
    _built: bool = field(default=False, repr=False)
    _contracts: Any = field(default=None, repr=False)

    def with_config(
        self,
        service_name: str | None = None,
        environment: str | None = None,
        **kwargs: Any,
    ) -> "BentoRuntime":
        """Configure runtime settings.

        Args:
            service_name: Service name for logging/tracing
            environment: Environment (local/dev/stage/prod)
            **kwargs: Additional config options

        Returns:
            Self for chaining
        """
        if service_name:
            self.config.service_name = service_name
        if environment:
            self.config.environment = environment
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        return self

    def with_contracts(
        self,
        path: str,
        require: bool = True,
    ) -> "BentoRuntime":
        """Enable contract validation.

        Args:
            path: Path to contracts directory
            require: If True, fail if contracts are missing

        Returns:
            Self for chaining
        """
        self.config.contracts_path = path
        self.config.require_contracts = require
        return self

    def with_modules(self, *modules: "BentoModule") -> "BentoRuntime":
        """Register application modules.

        Args:
            *modules: BentoModule instances

        Returns:
            Self for chaining
        """
        self.registry.register_all(*modules)
        return self

    def with_service(self, key: str, value: Any) -> "BentoRuntime":
        """Register a service in the container.

        Args:
            key: Service identifier
            value: Service instance

        Returns:
            Self for chaining
        """
        self.container.set(key, value)
        return self

    async def _run_gates(self) -> None:
        """Run startup gates (contract validation, etc.)."""
        if self.config.skip_gates_in_local and self.config.environment == "local":
            logger.debug("Skipping gates in local environment")
            return

        if not self.config.contracts_path:
            return

        contracts_dir = Path(self.config.contracts_path)
        if not contracts_dir.exists():
            if self.config.require_contracts:
                raise RuntimeError(f"Contracts directory not found: {contracts_dir}")
            return

        try:
            from bento.contracts import ContractLoader
            from bento.contracts.gates import ContractGate

            # Validate contracts
            gate = ContractGate(
                contracts_root=str(contracts_dir),
                require_state_machines=False,
                require_reason_codes=True,
            )
            gate.validate()

            # Load contracts
            self._contracts = ContractLoader.load_from_dir(str(contracts_dir.parent))

            # Register globally
            from bento.application.decorators import set_global_contracts
            from bento.core.exceptions import set_global_catalog

            if self._contracts.reason_codes:
                set_global_catalog(self._contracts.reason_codes)
            set_global_contracts(self._contracts)

            self.container.set("contracts", self._contracts)
            logger.info("Contracts loaded and validated")

        except ImportError:
            logger.warning("Contracts module not available, skipping validation")
        except Exception as e:
            if self.config.require_contracts:
                raise RuntimeError(f"Contract validation failed: {e}") from e
            logger.warning(f"Contract validation failed: {e}")

    async def _register_modules(self) -> None:
        """Register all modules in dependency order."""
        modules = self.registry.resolve_order()
        logger.info(f"Registering {len(modules)} modules: {[m.name for m in modules]}")

        for module in modules:
            logger.debug(f"Registering module: {module.name}")
            await module.on_register(self.container)

    async def _startup_modules(self) -> None:
        """Run startup hooks for all modules."""
        modules = self.registry.resolve_order()
        for module in modules:
            logger.debug(f"Starting module: {module.name}")
            await module.on_startup(self.container)

    async def _shutdown_modules(self) -> None:
        """Run shutdown hooks for all modules (reverse order)."""
        modules = list(reversed(self.registry.resolve_order()))
        for module in modules:
            logger.debug(f"Shutting down module: {module.name}")
            try:
                await module.on_shutdown(self.container)
            except Exception as e:
                logger.error(f"Error shutting down {module.name}: {e}")

    async def build_async(self) -> "BentoRuntime":
        """Build the runtime (async version).

        Runs gates and registers all modules.

        Returns:
            Self for chaining
        """
        if self._built:
            return self

        logger.info(f"Building runtime: {self.config.service_name}")

        # Store config in container
        self.container.set("config", self.config)

        # Run startup gates
        await self._run_gates()

        # Register modules
        await self._register_modules()

        self._built = True
        logger.info("Runtime built successfully")
        return self

    def build(self) -> "BentoRuntime":
        """Build the runtime (sync wrapper).

        For async applications, prefer build_async().

        Returns:
            Self for chaining
        """
        import asyncio

        try:
            asyncio.get_running_loop()
            # If we're in an async context, we can't use run()
            raise RuntimeError(
                "Cannot use build() in async context. Use 'await runtime.build_async()'"
            )
        except RuntimeError:
            # No running loop, safe to create one
            asyncio.run(self.build_async())

        return self

    def create_fastapi_app(
        self,
        title: str = "Bento API",
        description: str = "",
        version: str = "1.0.0",
        docs_url: str = "/docs",
        **fastapi_kwargs: Any,
    ) -> "FastAPI":
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
        from fastapi import FastAPI

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Build runtime if not already built
            if not self._built:
                await self.build_async()

            # Run module startup hooks
            await self._startup_modules()

            # Store runtime in app state
            app.state.runtime = self
            app.state.container = self.container

            logger.info(f"Application started: {title}")

            try:
                yield
            finally:
                # Run module shutdown hooks
                await self._shutdown_modules()
                logger.info(f"Application shutdown: {title}")

        app = FastAPI(
            title=title,
            description=description,
            version=version,
            docs_url=docs_url,
            lifespan=lifespan,
            **fastapi_kwargs,
        )

        # Collect and register routers from all modules
        for module in self.registry.resolve_order():
            for router in module.get_routers():
                app.include_router(router)

        # Add default health endpoint
        @app.get("/health")
        async def health():  # pyright: ignore[reportUnusedFunction]
            return {
                "status": "healthy",
                "service": self.config.service_name,
                "modules": self.registry.names(),
            }

        return app
