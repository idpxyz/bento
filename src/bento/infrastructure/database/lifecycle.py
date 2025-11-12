"""Database lifecycle management.

This module provides functions for database initialization, cleanup, and health checks.
"""

import logging
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)


async def init_database(
    engine: AsyncEngine,
    base: type[DeclarativeBase],
    *,
    check_tables: bool = True,
) -> None:
    """Initialize database by creating all tables.

    This function creates all tables defined in the provided Base's metadata.
    It's idempotent - running it multiple times won't cause errors.

    Args:
        engine: Async database engine
        base: SQLAlchemy DeclarativeBase class containing table definitions
        check_tables: Whether to check if tables already exist before creating

    Example:
        ```python
        from bento.infrastructure.database import create_async_engine_from_config, init_database
        from your_app.models import Base

        engine = create_async_engine_from_config(config)
        await init_database(engine, Base)
        ```

    Note:
        This is suitable for development and testing. In production,
        use a migration tool like Alembic for schema management.
    """
    logger.info(f"Initializing database tables from {base.__name__}...")

    try:
        async with engine.begin() as conn:
            if check_tables:
                # Check if any tables exist
                def check_table_exists(connection):
                    inspector = inspect(connection)
                    return len(inspector.get_table_names()) > 0

                has_tables = await conn.run_sync(check_table_exists)
                if has_tables:
                    logger.info("Tables already exist, skipping creation")
                else:
                    logger.info("No tables found, creating all tables")
                    await conn.run_sync(base.metadata.create_all)
            else:
                # Create all tables without checking
                await conn.run_sync(base.metadata.create_all)

        logger.info("Database initialization completed successfully")

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        raise


async def cleanup_database(engine: AsyncEngine) -> None:
    """Clean up database resources by closing all connections.

    This function should be called when shutting down the application
    to ensure proper cleanup of database connections.

    Args:
        engine: Async database engine to clean up

    Example:
        ```python
        from bento.infrastructure.database import cleanup_database

        # On application shutdown
        await cleanup_database(engine)
        ```
    """
    logger.info("Cleaning up database connections...")

    try:
        # Dispose of the connection pool
        await engine.dispose()
        logger.info("Database cleanup completed successfully")

    except Exception as e:
        logger.error(f"Error during database cleanup: {e}", exc_info=True)
        # Don't raise - we're shutting down anyway


async def health_check(engine: AsyncEngine, timeout: int = 5) -> bool:
    """Perform a database health check.

    This function attempts to execute a simple query to verify
    database connectivity and responsiveness.

    Args:
        engine: Async database engine
        timeout: Timeout in seconds for the health check

    Returns:
        True if database is healthy, False otherwise

    Example:
        ```python
        from bento.infrastructure.database import health_check

        is_healthy = await health_check(engine)
        if not is_healthy:
            logger.error("Database is not healthy!")
        ```
    """
    try:
        async with engine.connect() as conn:
            # Execute a simple query
            await conn.execute(text("SELECT 1"))

        logger.debug("Database health check passed")
        return True

    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


async def drop_all_tables(engine: AsyncEngine, base: type[DeclarativeBase]) -> None:
    """Drop all tables from the database.

    WARNING: This is a destructive operation! Use with caution.
    Primarily intended for testing environments.

    Args:
        engine: Async database engine
        base: SQLAlchemy DeclarativeBase class

    Example:
        ```python
        from bento.infrastructure.database import drop_all_tables

        # In test teardown
        await drop_all_tables(engine, Base)
        ```
    """
    logger.warning(f"Dropping all tables from {base.__name__}...")

    try:
        async with engine.begin() as conn:
            await conn.run_sync(base.metadata.drop_all)

        logger.info("All tables dropped successfully")

    except Exception as e:
        logger.error(f"Failed to drop tables: {e}", exc_info=True)
        raise


async def get_database_info(engine: AsyncEngine) -> dict[str, Any]:
    """Get database information and statistics.

    Args:
        engine: Async database engine

    Returns:
        Dictionary containing database information

    Example:
        ```python
        info = await get_database_info(engine)
        print(f"Database: {info['database_name']}")
        print(f"Pool size: {info['pool_size']}")
        ```
    """
    # Get pool info (some pools like NullPool don't have size/checkedout methods)
    pool_size = None
    pool_checked_out = None
    if hasattr(engine, "pool"):
        pool = engine.pool
        # Use getattr to safely access pool methods that may not exist
        size_method = getattr(pool, "size", None)
        checkedout_method = getattr(pool, "checkedout", None)
        pool_size = size_method() if callable(size_method) else None
        pool_checked_out = checkedout_method() if callable(checkedout_method) else None

    info = {
        "url": str(engine.url),
        "driver": engine.driver,
        "database_name": engine.url.database,
        "database_type": engine.dialect.name,
        "pool_size": pool_size,
        "pool_checked_out": pool_checked_out,
    }

    return info
