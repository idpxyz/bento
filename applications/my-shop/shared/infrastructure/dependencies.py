"""API Dependencies - Uses Bento Framework

This module provides FastAPI dependencies using Bento's infrastructure:
- Database session management
- Unit of Work pattern
- Repository access
- Port access
"""

from collections.abc import AsyncGenerator

from bento.infrastructure.database import create_async_engine_from_config
from bento.interfaces.fastapi import create_handler_dependency
from bento.persistence.outbox.record import SqlAlchemyOutbox
from bento.persistence.uow import SQLAlchemyUnitOfWork
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from config import settings

# Create database engine using Bento's configuration
db_config = settings.get_database_config()
engine = create_async_engine_from_config(db_config)

# Create session factory
session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session.

    Usage:
        @router.get("/items")
        async def get_items(session: AsyncSession = Depends(get_db_session)):
            ...
    """
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_uow(
    session: AsyncSession = Depends(get_db_session),
) -> AsyncGenerator[SQLAlchemyUnitOfWork, None]:
    """
    Get Unit of Work with Outbox pattern support and all repositories registered.

    The UnitOfWork manages:
    - Transaction boundaries
    - Repository lifecycle
    - Event collection and publishing
    - All domain repositories are pre-registered

    Usage:
        @router.post("/products")
        async def create_product(
            data: ProductCreate,
            uow: SQLAlchemyUnitOfWork = Depends(get_uow)
        ):
            async with uow:
                # Use repository (already registered)
                repo = uow.repository(Product)
                product = Product.create(...)
                await repo.save(product)
                # No need to manually track - repository handles it

                # Commit (saves changes + publishes events)
                await uow.commit()
    """
    outbox = SqlAlchemyOutbox(session)
    uow = SQLAlchemyUnitOfWork(session, outbox)

    # Import repositories to trigger @repository_for registration
    import contexts.catalog.infrastructure.repositories.category_repository_impl  # noqa: F401
    import contexts.catalog.infrastructure.repositories.product_repository_impl  # noqa: F401
    import contexts.identity.infrastructure.repositories.user_repository_impl  # noqa: F401
    import contexts.ordering.infrastructure.repositories.order_repository_impl  # noqa: F401

    # Auto-register all discovered repositories
    from bento.infrastructure.repository import get_repository_registry

    for ar_type, repo_cls in get_repository_registry().items():
        uow.register_repository(ar_type, lambda s, cls=repo_cls: cls(s))

    # Register outbound ports (adapters for cross-BC services)
    from contexts.ordering.domain.ports.services.i_product_catalog_service import (
        IProductCatalogService,
    )
    from contexts.ordering.infrastructure.adapters.adapter_factory import (
        get_product_catalog_adapter,
    )

    uow.register_port(
        IProductCatalogService,
        lambda s: get_product_catalog_adapter(s),
    )

    try:
        yield uow
    finally:
        # Cleanup is handled by UnitOfWork's __aexit__
        pass


# Create handler_dependency using Bento Framework's factory
# This provides clean DI for all CQRS handlers
handler_dependency = create_handler_dependency(get_uow)


# Legacy get_handler() function has been removed.
# All APIs now use handler_dependency() for clean OpenAPI schemas.


# ==================== Usage Examples ====================
#
# Elegant way (recommended):
# @router.post("/orders")
# async def create_order(
#     request: CreateOrderRequest,
#     handler: Annotated[CreateOrderHandler, handler_dependency(CreateOrderHandler)],
# ):
#     return await handler.execute(command)
#
# ❌ Old way (DEPRECATED - exposes handler_cls parameter):
# handler: Annotated[CreateOrderHandler, Depends(get_handler)]  # DON'T USE


# ==================== ARCHITECTURAL NOTES ====================
# UnitOfWork Port Container Pattern:
#
# UoW is NOT a Service Locator anti-pattern. It's a Transaction Context
# that provides resources relevant to the current request/transaction:
#
# 1. Repositories: uow.repository(AggregateType)
#    - Data access for aggregate roots
#
# 2. Outbound Ports: uow.port(PortType)
#    - Cross-BC communication interfaces
#    - External service adapters
#
# Scope:
# Register: Resources tied to current BC and transaction
# Don't register: Global services (logging, caching, etc.)
#
# Benefits:
# - Handlers have unified dependency (only UoW)
# - Clean architecture boundaries (Port/Adapter pattern)
# - Easy testing (mock UoW)
# - Lazy loading of resources
#
# New pattern (CORRECT - using universal handler factory):
#     @router.post("/orders")
#     async def create_order(
#         handler: Annotated[CreateOrderHandler, Depends(get_handler)],
#     ):
#         return await handler.execute(command)  # Session managed by FastAPI
# ===================================================
