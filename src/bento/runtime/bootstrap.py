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
class DatabaseConfig:
    """Database configuration for BentoRuntime."""

    url: str = ""
    echo: bool = False
    pool_size: int = 5
    max_overflow: int = 10


@dataclass
class RuntimeConfig:
    """Configuration for BentoRuntime."""

    contracts_path: str | None = None
    require_contracts: bool = False
    environment: str = "local"
    service_name: str = "bento-app"
    skip_gates_in_local: bool = True
    database: DatabaseConfig | None = None


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
    _session_factory: Any = field(default=None, repr=False)
    _get_uow_func: Any = field(default=None, repr=False)
    _handler_dependency_func: Any = field(default=None, repr=False)

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

    def with_database(
        self,
        url: str | None = None,
        config: DatabaseConfig | None = None,
        **kwargs: Any,
    ) -> "BentoRuntime":
        """Configure database connection.

        Args:
            url: Database URL (shorthand)
            config: Full DatabaseConfig object
            **kwargs: Additional database config options

        Returns:
            Self for chaining

        Example:
            ```python
            runtime.with_database(url="postgresql+asyncpg://...")
            # or
            runtime.with_database(config=DatabaseConfig(url="...", pool_size=10))
            ```
        """
        if config:
            self.config.database = config
        elif url:
            self.config.database = DatabaseConfig(url=url, **kwargs)
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

            # Auto-scan packages to trigger @repository_for decorators
            self._scan_module_packages(module)

            await module.on_register(self.container)

    def _scan_module_packages(self, module: "BentoModule") -> None:
        """Scan module's declared packages to trigger decorator registration."""
        import importlib

        for package_name in module.scan_packages:
            try:
                importlib.import_module(package_name)
                logger.debug(f"Scanned package: {package_name}")
            except ImportError as e:
                logger.warning(f"Failed to scan package {package_name}: {e}")

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

    def _setup_database(self) -> None:
        """Setup database session factory."""
        if self._session_factory is not None:
            return

        if not self.config.database or not self.config.database.url:
            logger.warning("No database configured, DI functions won't be available")
            return

        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

        engine = create_async_engine(
            self.config.database.url,
            echo=self.config.database.echo,
            pool_size=self.config.database.pool_size,
            max_overflow=self.config.database.max_overflow,
        )
        self._session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
        self.container.set("db.engine", engine)
        self.container.set("db.session_factory", self._session_factory)
        logger.info("Database configured")

    @property
    def get_uow(self):
        """Get the UnitOfWork dependency function for FastAPI.

        Returns:
            FastAPI Depends-compatible async generator function

        Example:
            ```python
            @router.post("/products")
            async def create_product(uow: UnitOfWork = Depends(runtime.get_uow)):
                ...
            ```
        """
        if self._get_uow_func is not None:
            return self._get_uow_func

        self._setup_database()

        if not self._session_factory:
            raise RuntimeError("Database not configured. Call with_database() first.")

        from collections.abc import AsyncGenerator

        from fastapi import Depends

        from bento.infrastructure.ports import get_port_registry
        from bento.infrastructure.repository import get_repository_registry
        from bento.persistence.outbox.record import SqlAlchemyOutbox
        from bento.persistence.uow import SQLAlchemyUnitOfWork

        session_factory = self._session_factory

        async def get_db_session() -> AsyncGenerator:
            async with session_factory() as session:
                try:
                    yield session
                finally:
                    await session.close()

        async def get_uow(
            session=Depends(get_db_session),
        ) -> AsyncGenerator[SQLAlchemyUnitOfWork, None]:
            outbox = SqlAlchemyOutbox(session)
            uow = SQLAlchemyUnitOfWork(session, outbox)

            # Auto-register all discovered repositories
            for ar_type, repo_cls in get_repository_registry().items():
                uow.register_repository(ar_type, lambda s, cls=repo_cls: cls(s))

            # Auto-register all discovered ports
            for port_type, adapter_cls in get_port_registry().items():
                uow.register_port(port_type, lambda s, cls=adapter_cls: cls(s))

            try:
                yield uow
            finally:
                pass

        self._get_uow_func = get_uow
        return self._get_uow_func

    @property
    def handler_dependency(self):
        """Get the handler dependency factory for FastAPI.

        Returns:
            Handler dependency factory function

        Example:
            ```python
            @router.post("/products")
            async def create_product(
                handler: Annotated[CreateProductHandler, runtime.handler_dependency(CreateProductHandler)],
            ):
                ...
            ```
        """
        if self._handler_dependency_func is not None:
            return self._handler_dependency_func

        from bento.interfaces.fastapi import create_handler_dependency

        self._handler_dependency_func = create_handler_dependency(self.get_uow)
        return self._handler_dependency_func
