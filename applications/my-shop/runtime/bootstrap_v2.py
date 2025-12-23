"""Application bootstrap for my-shop using BentoRuntime.

This is the new composition root using the unified bento.runtime module.
It combines LOMS-style module registry with Bento's FastAPI integration.

Example:
    from runtime.bootstrap_v2 import create_app
    app = create_app()
"""

from __future__ import annotations

import logging

from bento.runtime import BentoRuntime
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from runtime.modules.catalog import CatalogModule
from runtime.modules.identity import IdentityModule
from runtime.modules.infra import InfraModule
from runtime.modules.ordering import OrderingModule
from shared.exceptions.handlers import (
    generic_exception_handler,
    response_validation_exception_handler,
    validation_exception_handler,
)

logger = logging.getLogger(__name__)


def create_runtime() -> BentoRuntime:
    """Create and configure the BentoRuntime."""
    return (
        BentoRuntime()
        .with_config(
            service_name="my-shop",
            environment=settings.environment if hasattr(settings, "environment") else "local",
        )
        .with_modules(
            InfraModule(),
            CatalogModule(),
            IdentityModule(),
            OrderingModule(),
        )
    )


def create_app() -> FastAPI:
    """Create and configure FastAPI application using BentoRuntime."""
    runtime = create_runtime()

    # Create FastAPI app with BentoRuntime lifespan
    app = runtime.create_fastapi_app(
        title=settings.app_name,
        description="完整测试项目 - Powered by BentoRuntime",
        version="0.2.0",
        docs_url="/docs",
        redoc_url="/redoc",
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
            "runtime": "BentoRuntime",
        }

    @app.get("/ping")
    async def ping():  # pyright: ignore[reportUnusedFunction]
        return {"message": "pong"}

    logger.info("FastAPI application created with BentoRuntime")

    return app
