"""Application bootstrap for my-shop using BentoRuntime.

This is the new composition root using the unified bento.runtime module.
It combines LOMS-style module registry with Bento's FastAPI integration.

Best Practices Applied:
- Async runtime initialization with build_async()
- Proper lifecycle management with FastAPI lifespan
- Graceful shutdown handling

Example:
    from runtime.bootstrap_v2 import create_app
    app = create_app()
"""

from __future__ import annotations

import logging
import sys

from bento.runtime import BentoRuntime
from bento.runtime.builder.runtime_builder import RuntimeBuilder
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from runtime.modules.catalog import CatalogModule
from runtime.modules.identity import IdentityModule
from runtime.modules.infra import InfraModule
from runtime.modules.ordering import OrderingModule
from runtime.modules.service_discovery import create_service_discovery_module
from shared.exceptions import (
    generic_exception_handler,
    response_validation_exception_handler,
    validation_exception_handler,
)
from shared.infrastructure.idempotency_middleware import idempotency_middleware

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)

logger = logging.getLogger(__name__)


def build_runtime() -> BentoRuntime:
    """Build runtime configuration (without async initialization).

    Returns:
        Configured but not yet initialized BentoRuntime
    """
    return (
        RuntimeBuilder()
        .with_config(
            service_name="my-shop",
            environment=settings.app_env,
        )
        .with_database(url=settings.database_url)
        .with_modules(
            InfraModule(),
            CatalogModule(),
            IdentityModule(),
            OrderingModule(),
            create_service_discovery_module(),
        )
        .build_runtime()
    )


# Global runtime instance for DI exports
_runtime: BentoRuntime | None = None


def get_runtime() -> BentoRuntime:
    """Get or create the global runtime instance.

    Note: Returns runtime without async initialization for DI purposes.
    Actual initialization happens in FastAPI lifespan (via create_fastapi_app).

    Returns:
        BentoRuntime instance (may not be fully initialized yet)
    """
    global _runtime
    if _runtime is None:
        _runtime = build_runtime()
        logger.info("BentoRuntime instance created (will be initialized in lifespan)")
    return _runtime


def create_app() -> FastAPI:
    """Create and configure FastAPI application using BentoRuntime.

    Best Practice Version:
    - Runtime's built-in lifespan handles startup/shutdown
    - Async runtime initialization via build_async()
    - Graceful resource cleanup via lifecycle manager

    Note: BentoRuntime.create_fastapi_app() includes built-in lifespan
    that handles:
    - Runtime initialization (build_async)
    - Module startup hooks
    - Module shutdown hooks
    - Database cleanup
    """
    logger.info(f"Creating FastAPI application: {settings.app_name}")
    logger.debug(f"Environment: {settings.app_env}, Database: {settings.database_url}")

    runtime = build_runtime()
    logger.debug("BentoRuntime configured with modules: infra, catalog, identity, ordering, service_discovery")

    # Create FastAPI app with BentoRuntime's built-in lifespan
    # The lifespan will handle build_async() and module initialization
    app = runtime.create_fastapi_app(
        title=settings.app_name,
        description="Complete test project - Powered by BentoRuntime (Best Practice)",
        version="0.2.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    logger.debug("FastAPI app created with BentoRuntime's built-in lifespan")

    # Add idempotency middleware (must be before CORS)
    app.middleware("http")(idempotency_middleware)
    logger.debug("Idempotency middleware registered")

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.debug(f"CORS middleware configured with origins: {settings.cors_origins}")

    # Add exception handlers
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ResponseValidationError, response_validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
    logger.debug("Exception handlers registered")

    # Add custom routes
    @app.get("/")
    async def root():  # pyright: ignore[reportUnusedFunction]
        return {
            "message": f"Welcome to {settings.app_name}",
            "status": "running",
            "docs": "/docs",
            "runtime": "BentoRuntime (Best Practice)",
        }

    @app.get("/ping")
    async def ping():  # pyright: ignore[reportUnusedFunction]
        return {"message": "pong"}

    @app.get("/health")
    async def health():  # pyright: ignore[reportUnusedFunction]
        """Health check endpoint with runtime status."""
        runtime_status = "initialized" if hasattr(app.state, "runtime") else "not_initialized"
        return {
            "status": "healthy",
            "runtime": runtime_status,
            "service": settings.app_name,
            "environment": settings.app_env,
        }
    logger.debug("Custom routes registered: /, /ping, /health")

    logger.info(f"FastAPI application created successfully: {settings.app_name} (Best Practice)")
    logger.info(f"API documentation available at: /docs")

    return app
