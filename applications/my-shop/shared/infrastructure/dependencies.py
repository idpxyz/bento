"""API Dependencies - Bento Framework Best Practice

This module provides FastAPI dependencies using Bento's infrastructure.
Follows Bento Framework best practice: all database resources come from
BentoRuntime's container.

Architecture:
- Database engine and session_factory are managed by BentoRuntime
- No duplicate resource creation
- Single source of truth: BentoRuntime container

Usage:
    from shared.infrastructure.dependencies import get_uow

    @router.post("/items")
    async def create_item(
        uow: SQLAlchemyUnitOfWork = Depends(get_uow)
    ):
        async with uow:
            ...
"""

from collections.abc import AsyncGenerator

from bento.interfaces.fastapi import create_handler_dependency
from bento.persistence.outbox.record import SqlAlchemyOutbox
from bento.persistence.uow import SQLAlchemyUnitOfWork
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession


def _get_container():
    """Get BentoRuntime container.

    Returns:
        BentoContainer instance

    Raises:
        RuntimeError: If runtime is not initialized
    """
    from runtime.bootstrap_v2 import get_runtime

    runtime = get_runtime()
    return runtime.container


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session from BentoRuntime container.

    Best Practice: Uses session_factory from BentoRuntime container.

    Usage:
        @router.get("/items")
        async def get_items(session: AsyncSession = Depends(get_db_session)):
            ...
    """
    container = _get_container()

    # Get session_factory from container
    # It's set by BentoRuntime's DatabaseManager during build_async()
    try:
        session_factory = container.get("db.session_factory")
    except KeyError:
        # Fallback: create standalone session factory if not in container
        # This can happen if runtime hasn't fully initialized yet
        from shared.infrastructure.standalone_db import get_standalone_session_factory
        session_factory = get_standalone_session_factory()

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

    # Auto-register all discovered repositories and ports
    # - Production: scanned by BentoModule.scan_packages during startup
    # - Tests: scanned by conftest.py
    from bento.infrastructure.ports import get_port_registry
    from bento.infrastructure.repository import get_repository_registry

    for ar_type, repo_cls in get_repository_registry().items():
        uow.register_repository(ar_type, lambda s, cls=repo_cls: cls(s))

    for port_type, adapter_cls in get_port_registry().items():
        uow.register_port(port_type, lambda s, cls=adapter_cls: cls(s))

    try:
        yield uow
    finally:
        # Cleanup is handled by UnitOfWork's __aexit__
        pass


# Create handler_dependency using Bento Framework's factory
# This provides clean DI for all CQRS handlers
handler_dependency = create_handler_dependency(get_uow)


# ==================== Public API ====================
# This module exports:
# - get_db_session: Get database session
# - get_uow: Get Unit of Work
# - handler_dependency: Inject CQRS handlers
#
# Usage in FastAPI routes:
#
# 1. Direct database access:
#    @router.get("/items")
#    async def get_items(session: AsyncSession = Depends(get_db_session)):
#        ...
#
# 2. Unit of Work pattern:
#    @router.post("/items")
#    async def create_item(uow: SQLAlchemyUnitOfWork = Depends(get_uow)):
#        async with uow:
#            ...
#
# 3. CQRS Handler injection (recommended):
#    @router.post("/orders")
#    async def create_order(
#        handler: Annotated[CreateOrderHandler, handler_dependency(CreateOrderHandler)]
#    ):
#        return await handler.execute(command)


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
#         handler: Annotated[CreateOrderHandler, handler_dependency(CreateOrderHandler)],
#     ):
#         return await handler.execute(command)  # Session managed by FastAPI
# ===================================================
