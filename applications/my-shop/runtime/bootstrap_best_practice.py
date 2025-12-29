"""Application bootstrap for my-shop - Best Practice Version.

This version follows Bento Runtime best practices:
1. Async runtime initialization with build_async()
2. Proper lifecycle management with FastAPI lifespan
3. Graceful shutdown handling
4. Runtime instance caching with proper initialization
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

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
from shared.exceptions.handlers import (
    generic_exception_handler,
    response_validation_exception_handler,
    validation_exception_handler,
)

logger = logging.getLogger(__name__)


# Global runtime instance
_runtime: BentoRuntime | None = None


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


async def get_runtime() -> BentoRuntime:
    """Get or create and initialize the global runtime instance.

    This ensures runtime is properly initialized with build_async().

    Returns:
        Initialized BentoRuntime instance
    """
    global _runtime
    if _runtime is None:
        _runtime = build_runtime()
        await _runtime.build_async()
        logger.info("BentoRuntime initialized successfully")
    return _runtime


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager for runtime lifecycle.

    Handles:
    - Runtime initialization on startup
    - Graceful shutdown on application exit

    Note: BentoRuntime.create_fastapi_app() already includes a built-in lifespan
    that handles initialization and shutdown, so this is for reference only.
    """
    # Startup
    logger.info("Starting my-shop application...")
    runtime = build_runtime()
    await runtime.build_async()

    # Store runtime in app state for access in routes
    app.state.runtime = runtime

    logger.info("my-shop application started successfully")

    yield

    # Shutdown
    logger.info("Shutting down my-shop application...")
    # Use lifecycle manager for graceful shutdown
    await runtime._lifecycle_manager.shutdown()
    logger.info("my-shop application shutdown complete")


def create_app() -> FastAPI:
    """Create and configure FastAPI application using BentoRuntime.

    Best Practice Version:
    - Uses lifespan for proper startup/shutdown
    - Async runtime initialization
    - Graceful resource cleanup

    Returns:
        Configured FastAPI application
    """
    # Build runtime (without async init - will be done in lifespan)
    runtime = build_runtime()

    # Create FastAPI app with BentoRuntime and lifespan
    app = runtime.create_fastapi_app(
        title=settings.app_name,
        description="完整测试项目 - Powered by BentoRuntime (Best Practice)",
        version="0.2.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,  # ✅ Proper lifecycle management
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add exception handlers
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ResponseValidationError, response_validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

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

    logger.info("FastAPI application created with BentoRuntime (Best Practice)")

    return app
