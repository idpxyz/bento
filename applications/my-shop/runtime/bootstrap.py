"""Application bootstrap for my-shop using BentoRuntime.

This is the new composition root using the unified bento.runtime module.
Refactored for better maintainability with separated concerns:
- runtime_config.py: Runtime and module configuration
- middleware_config.py: Middleware stack configuration
- app_config.py: Routes, exception handlers, and OpenAPI setup

Best Practices Applied:
- Async runtime initialization with build_async()
- Proper lifecycle management with FastAPI lifespan
- Graceful shutdown handling
- Separated configuration concerns

Example:
    from runtime.bootstrap_v2 import create_app
    app = create_app()
"""

from __future__ import annotations

import logging
import sys

from fastapi import FastAPI

from config import settings
from runtime.config import (
    build_runtime,
    configure_exception_handlers,
    configure_middleware,
    configure_openapi,
    configure_routes,
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure FastAPI application using BentoRuntime.

    Best Practice Version:
    - Runtime's built-in lifespan handles startup/shutdown
    - Async runtime initialization via build_async()
    - Graceful resource cleanup via lifecycle manager
    - Separated configuration concerns for better maintainability

    Returns:
        Configured FastAPI application
    """
    logger.info(f"Creating FastAPI application: {settings.app_name}")
    logger.debug(f"Environment: {settings.app_env}, Database: {settings.database_url}")

    # Build runtime with all modules
    runtime = build_runtime()
    logger.debug("BentoRuntime configured with modules: infra, catalog, identity, ordering, service_discovery, observability")

    # Create FastAPI app with BentoRuntime's built-in lifespan
    app = runtime.create_fastapi_app(
        title=settings.app_name,
        description="Complete test project - Powered by BentoRuntime (Best Practice)",
        version="0.2.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    logger.debug("FastAPI app created with BentoRuntime's built-in lifespan")

    # Store runtime in app.state for middleware access
    app.state.bento_runtime = runtime
    logger.debug("BentoRuntime stored in app.state for middleware access")

    # Configure middleware stack (order matters!)
    configure_middleware(app, runtime)

    # Configure exception handlers
    configure_exception_handlers(app)

    # Configure routes
    configure_routes(app)

    # Configure OpenAPI customization
    configure_openapi(app)

    logger.info(f"FastAPI application created successfully: {settings.app_name} (Best Practice)")
    logger.info("API documentation available at: /docs")

    return app
