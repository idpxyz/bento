"""Composition root for dependency injection.

This module wires up all dependencies for the e-commerce application.
Uses Bento's database infrastructure for configuration and lifecycle management.
"""

import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from applications.ecommerce.modules.order.domain.order import Order
from applications.ecommerce.modules.order.persistence import OrderRepository
from bento.application.ports import IUnitOfWork
from bento.infrastructure.database import (
    DatabaseConfig,
    cleanup_database,
    create_async_engine_from_config,
    create_async_session_factory,
    drop_all_tables,
    init_database,
)
from bento.persistence import Base
from bento.persistence.sqlalchemy.outbox_sql import SqlAlchemyOutbox
from bento.persistence.uow import UnitOfWork

# ==================== Database Configuration ====================

# Load database configuration from environment variables
# Set DB_URL, DB_POOL_SIZE, DB_ECHO, etc. to override defaults
db_config = DatabaseConfig()

# Create engine and session factory using Bento infrastructure
engine: AsyncEngine = create_async_engine_from_config(db_config)
async_session_factory: async_sessionmaker[AsyncSession] = create_async_session_factory(engine)


# ==================== Repository Factory ====================


def create_order_repository(session: AsyncSession) -> OrderRepository:
    """Create order repository (legacy simple implementation).

    Args:
        session: Database session

    Returns:
        Order repository instance (without Interceptors)

    Note:
        This is the simple implementation for demonstration purposes.
        Use create_order_repository_with_interceptors for production.
    """
    return OrderRepository(session)


def create_order_repository_with_interceptors(
    session: AsyncSession, actor: str = "system"
) -> OrderRepository:
    """Create order repository with Interceptor support (recommended).

    Args:
        session: Database session
        actor: Current actor/user identifier for audit tracking

    Returns:
        Order repository with automatic audit/soft-delete/optimistic-lock support

    Features:
        - Automatic audit fields (created_at, updated_at, created_by, updated_by)
        - Soft delete support (deleted_at, deleted_by)
        - Optimistic locking (version field)

    Example:
        ```python
        async with get_session() as session:
            repo = create_order_repository_with_interceptors(
                session, actor="user-123"
            )
            order = Order(order_id=ID.generate(), customer_id=customer_id)
            await repo.save(order)
            # ↑ Audit fields automatically populated
        ```
    """
    return OrderRepository(
        session=session,
        actor=actor,
    )


# ==================== Unit of Work ====================


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session.

    Yields:
        Database session
    """
    async with async_session_factory() as session:
        yield session


async def get_unit_of_work(actor: str = "system", use_interceptors: bool = True) -> IUnitOfWork:
    """Get unit of work.

    Args:
        actor: Current actor/user identifier for audit tracking
        use_interceptors: Whether to use repositories with Interceptor support

    Returns:
        Unit of work instance with repositories registered

    Note:
        When use_interceptors=True (default), repositories will have:
        - Automatic audit fields
        - Soft delete support
        - Optimistic locking
    """
    # Ensure database is initialized
    await init_db()

    # Get session
    session = async_session_factory()

    # Create outbox first
    outbox = SqlAlchemyOutbox(session)

    # Create unit of work with outbox
    uow = UnitOfWork(session=session, outbox=outbox, repository_factories={})

    # Register repository factories
    # Note: OrderRepository always includes interceptor support
    repository_factories = {
        Order: lambda s: OrderRepository(
            session=s,
            actor=actor,
        ),
    }

    # Update the repository factories
    uow._repository_factories = repository_factories

    return uow


# ==================== Database Initialization ====================


# Track initialization state
_db_initialized = False


async def init_db() -> None:
    """Initialize database using Bento infrastructure.

    Creates all tables if they don't exist.
    This is idempotent - safe to call multiple times.
    """
    global _db_initialized

    # Skip if already initialized (for performance)
    if _db_initialized:
        return

    # Import framework models (Outbox) - must import models to register them
    from bento.persistence.sqlalchemy.base import Base as FrameworkBase

    # In test mode, reset the application schema to avoid stale columns
    reset_flag = os.getenv("BENTO_TEST_RESET_DB")
    is_pytest = "PYTEST_CURRENT_TEST" in os.environ
    if (reset_flag and reset_flag.lower() in {"1", "true", "yes"}) or is_pytest:
        await drop_all_tables(engine, Base)
        await init_database(engine, Base, check_tables=False)
    else:
        # Initialize application tables (idempotent create if empty)
        await init_database(engine, Base, check_tables=True)

    # Initialize framework tables (Outbox) - use check_tables=False to force creation
    await init_database(engine, FrameworkBase, check_tables=False)

    _db_initialized = True


async def close_db() -> None:
    """Close database connections using Bento infrastructure."""
    await cleanup_database(engine)
