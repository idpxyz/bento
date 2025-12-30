"""Application bootstrap.

Initializes and configures the FastAPI application.
"""

import logging
from contextlib import asynccontextmanager

from bento.core.error_handler import register_exception_handlers
from fastapi import FastAPI

from applications.ecommerce.modules.order.interfaces import router as order_router
from applications.ecommerce.runtime.composition import close_db, init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting e-commerce application...")
    await init_db()
    logger.info("Database initialized")

    yield

    # Shutdown
    logger.info("Shutting down e-commerce application...")
    await close_db()
    logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    """Create and configure FastAPI application.

    Returns:
        Configured FastAPI application
    """
    # Create FastAPI app
    app = FastAPI(
        title="E-commerce API",
        description="A DDD-based e-commerce system built with the Bento framework",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Register exception handlers
    register_exception_handlers(app)

    # Register routers
    app.include_router(
        order_router,
        prefix="/api/orders",
        tags=["orders"],
    )

    # Health check endpoint
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy"}

    app.add_api_route("/health", health_check, methods=["GET"])

    logger.info("FastAPI application created successfully")

    return app
