"""Composition root for dependency injection.

This module wires up all dependencies for the e-commerce application.
Uses Bento's database infrastructure for configuration and lifecycle management.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from applications.ecommerce.modules.order.adapters.order_repository import (
    OrderRepository,
)
from applications.ecommerce.modules.order.domain.order import Order
from applications.ecommerce.persistence.models import Base
from bento.application.ports import IUnitOfWork
from bento.infrastructure.database import (
    DatabaseConfig,
    cleanup_database,
    create_async_engine_from_config,
    create_async_session_factory,
    init_database,
)
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
    """Create order repository.

    Args:
        session: Database session

    Returns:
        Order repository instance
    """
    return OrderRepository(session)


# ==================== Unit of Work ====================


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session.

    Yields:
        Database session
    """
    async with async_session_factory() as session:
        yield session


async def get_unit_of_work() -> IUnitOfWork:
    """Get unit of work.

    Returns:
        Unit of work instance with repositories registered
    """
    # Ensure database is initialized
    await init_db()

    # Get session
    session = async_session_factory()

    # Create outbox first
    outbox = SqlAlchemyOutbox(session)

    # Create unit of work with outbox
    uow = UnitOfWork(session=session, outbox=outbox, repository_factories={})

    # Register repository factories that have access to uow
    repository_factories = {
        Order: lambda s: OrderRepository(s, uow=uow),
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

    # Import framework models (Outbox)
    from bento.persistence.sqlalchemy.base import Base as FrameworkBase

    # Initialize application tables
    await init_database(engine, Base, check_tables=True)

    # Initialize framework tables (Outbox)
    await init_database(engine, FrameworkBase, check_tables=True)

    _db_initialized = True


async def close_db() -> None:
    """Close database connections using Bento infrastructure."""
    await cleanup_database(engine)
