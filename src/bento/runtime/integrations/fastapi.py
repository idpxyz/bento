"""FastAPI integration for Bento Runtime."""

import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fastapi import FastAPI

    from bento.runtime.bootstrap import BentoRuntime

logger = logging.getLogger(__name__)


class FastAPIIntegration:
    """Handles FastAPI application creation and configuration."""

    def __init__(self, runtime: "BentoRuntime") -> None:
        """Initialize FastAPI integration.

        Args:
            runtime: BentoRuntime instance
        """
        self.runtime = runtime

    def create_app(
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
        async def lifespan(app: "FastAPI"):
            # Build runtime if not already built
            if not self.runtime._built:
                await self.runtime.build_async()

            # Run module startup hooks via lifecycle manager
            await self.runtime._lifecycle_manager._startup_modules()

            # Store runtime in app state
            app.state.runtime = self.runtime
            app.state.container = self.runtime.container

            logger.info(f"Application started: {title}")

            try:
                yield
            finally:
                # Run module shutdown hooks via lifecycle manager
                await self.runtime._lifecycle_manager._shutdown_modules()

                # Cleanup database connections
                await self.runtime._lifecycle_manager._cleanup_database()

                logger.info(f"Application shutdown: {title}")

        app = FastAPI(
            title=title,
            description=description,
            version=version,
            docs_url=docs_url,
            lifespan=lifespan,
            **fastapi_kwargs,
        )

        # Register middleware, routers, and endpoints
        self._register_middleware(app)
        self._register_routers(app)
        self._setup_health_endpoint(app)
        self._register_exception_handlers(app)

        return app

    def _register_middleware(self, app: "FastAPI") -> None:
        """Register middleware from all modules."""
        all_middleware: list[Any] = []
        for module in self.runtime.registry.resolve_order():
            all_middleware.extend(module.get_middleware())

        # Add middleware (in reverse order for correct execution)
        for middleware in reversed(all_middleware):
            app.add_middleware(middleware.cls, **middleware.kwargs)

    def _register_routers(self, app: "FastAPI") -> None:
        """Register routers from all modules."""
        for module in self.runtime.registry.resolve_order():
            for item in module.get_routers():
                if isinstance(item, tuple):
                    router, prefix = item
                    app.include_router(router, prefix=prefix)
                else:
                    app.include_router(item)

    def _setup_health_endpoint(self, app: "FastAPI") -> None:
        """Setup default health endpoint with optional database check."""

        @app.get("/health")
        async def health():  # pyright: ignore[reportUnusedFunction]
            result = {
                "status": "healthy",
                "service": self.runtime.config.service_name,
                "modules": self.runtime.registry.names(),
            }

            # Add database health if configured
            if self.runtime.config.database and self.runtime.config.database.url:
                try:
                    engine = self.runtime.container.get("db.engine")
                    if engine:
                        from bento.infrastructure.database import health_check

                        db_healthy = await health_check(engine)
                        result["database"] = "healthy" if db_healthy else "unhealthy"
                        if not db_healthy:
                            result["status"] = "degraded"
                except Exception:
                    result["database"] = "unknown"

            return result

    def _register_exception_handlers(self, app: "FastAPI") -> None:
        """Register exception handlers."""
        from bento.core.exception_handler import register_exception_handlers

        register_exception_handlers(app)
