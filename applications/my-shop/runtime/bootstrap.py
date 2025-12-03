"""Application bootstrap for my-shop.

Provides FastAPI application creation and lifespan management.

This is the composition root for the my-shop application:
- Configures FastAPI (title, docs, middleware)
- Registers global exception handlers
- Aggregates routers via router_registry
- Provides an async lifespan hook for future startup/shutdown logic
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager

from bento.adapters.cache import CacheBackend, CacheConfig, CacheFactory
from bento.adapters.messaging.inprocess import InProcessMessageBus
from bento.infrastructure.projection.projector import OutboxProjector
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.middleware.cors import CORSMiddleware

from config import settings  # Config package exports settings from top-level config.py
from config.warmup_config import setup_cache_warmup
from contexts.catalog.infrastructure.repositories.category_repository_impl import (
    CategoryRepository,
)
from contexts.catalog.infrastructure.repositories.product_repository_impl import (
    ProductRepository,
)
from contexts.ordering.domain.events.ordercancelled_event import (  # noqa: F401
    OrderCancelledEvent,
)
from contexts.ordering.domain.events.ordercreated_event import (  # noqa: F401
    OrderCreatedEvent,
)
from contexts.ordering.domain.events.orderdelivered_event import (  # noqa: F401
    OrderDeliveredEvent,
)
from contexts.ordering.domain.events.orderpaid_event import (  # noqa: F401
    OrderPaidEvent,
)
from contexts.ordering.domain.events.ordershipped_event import (  # noqa: F401
    OrderShippedEvent,
)
from shared.api.router_registry import create_api_router
from shared.exceptions.handlers import (
    generic_exception_handler,
    response_validation_exception_handler,
    validation_exception_handler,
)
from shared.infrastructure.dependencies import session_factory

# Explicitly reference event classes to satisfy linter (imports are needed for registration)
_REGISTERED_EVENTS = (
    OrderCancelledEvent,
    OrderCreatedEvent,
    OrderDeliveredEvent,
    OrderPaidEvent,
    OrderShippedEvent,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):  # pragma: no cover - thin wiring layer
    """Application lifespan manager.

    Currently used for structured startup/shutdown logging and as a hook for
    background workers (e.g. Outbox consumers / projection workers).

    The default implementation starts a lightweight background task that can be
    extended later to:
    - Poll the Outbox table for NEW events
    - Dispatch events to a message bus or projection handlers
    - Mark events as PUBLISHED / FAILED with retry
    """
    logger.info("Starting my-shop application ...")

    # Create in-process bus and projector
    bus = InProcessMessageBus(source="my-shop")
    projector = OutboxProjector(
        session_factory=session_factory,
        message_bus=bus,
        tenant_id="default",
    )

    # Start bus and projector loop
    await bus.start()
    projector_task = asyncio.create_task(projector.run_forever())

    # Setup cache and warmup (production-ready)
    cache = await CacheFactory.create(
        CacheConfig(
            backend=CacheBackend.MEMORY,  # 生产环境改为 REDIS
            ttl=300,
        )
    )

    # Create repositories for warmup (use dependency injection in production)
    async with session_factory() as session:
        from contexts.catalog.domain.ports.repositories.i_category_repository import (
            ICategoryRepository,
        )
        from contexts.catalog.domain.ports.repositories.i_product_repository import (
            IProductRepository,
        )

        product_repo: IProductRepository = ProductRepository(session, actor="system")
        category_repo: ICategoryRepository = CategoryRepository(session, actor="system")

        # Setup and execute cache warmup
        warmup_coordinator = await setup_cache_warmup(
            cache,
            product_repository=product_repo,
            category_repository=category_repo,
            warmup_on_startup=True,  # 启动时立即预热
            max_concurrency=20,
        )

    # Store in app state for later use (e.g., manual warmup endpoints)
    app.state.cache = cache
    app.state.warmup_coordinator = warmup_coordinator

    try:
        # Startup logic hook (keep light here; heavy work should be offloaded)
        yield
    finally:
        # Graceful shutdown of projector and bus
        await projector.stop()
        projector_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await projector_task

        await bus.stop()

        logger.info("Shutting down my-shop application ...")


def create_app() -> FastAPI:
    """Create and configure FastAPI application with lifespan."""
    app = FastAPI(
        title=settings.app_name,
        description="完整测试项目",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ResponseValidationError, response_validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    api_router = create_api_router()
    app.include_router(api_router, prefix="/api/v1")

    @app.get("/")
    async def root():  # type: ignore[func-returns-value]
        return {
            "message": f"Welcome to {settings.app_name}",
            "status": "running",
            "docs": "/docs",
        }

    @app.get("/ping")
    async def ping():  # type: ignore[func-returns-value]
        return {"message": "pong"}

    @app.get("/health")
    async def health():  # type: ignore[func-returns-value]
        return {"status": "healthy", "service": "my-shop"}

    logger.info("FastAPI application created successfully")

    return app


# 在 lifespan 里挂 定时 job / outbox 消费器 / projection worker，我们可以直接在
# runtime/bootstrap.py 上加，不会影响现有 API 结构。

# 1. 定时 job
# 2. outbox 消费器
# 3. projection worker
