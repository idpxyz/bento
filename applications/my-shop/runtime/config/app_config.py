"""Application Configuration - Routes and exception handlers setup.

Responsible for configuring routes, exception handlers, and OpenAPI customization.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError, ResponseValidationError

from bento.core.exceptions import ApplicationException
from bento.runtime.integrations import setup_bento_openapi

from config import settings
from shared.exceptions import (
    application_exception_handler,
    generic_exception_handler,
    response_validation_exception_handler,
    validation_exception_handler,
)

logger = logging.getLogger(__name__)


def configure_exception_handlers(app: FastAPI) -> None:
    """Configure exception handlers for the FastAPI application.

    Args:
        app: FastAPI application instance
    """
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ResponseValidationError, response_validation_exception_handler)
    app.add_exception_handler(ApplicationException, application_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
    logger.debug("Exception handlers registered")


def configure_routes(app: FastAPI) -> None:
    """Configure routes for the FastAPI application.

    Args:
        app: FastAPI application instance
    """
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

    # Register auth routes
    from shared.api.auth_routes import router as auth_router
    app.include_router(auth_router, prefix="/api/v1")
    logger.info("✅ Auth routes registered (GET /api/v1/auth/me, GET /api/v1/auth/me/context)")


def configure_openapi(app: FastAPI) -> None:
    """Configure OpenAPI schema customization.

    Args:
        app: FastAPI application instance
    """
    setup_bento_openapi(app)
    logger.info("✅ Custom OpenAPI schema configured (X-Idempotency-Key, X-Tenant-ID, X-Request-ID)")
