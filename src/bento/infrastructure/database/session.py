"""Database session factory.

This module provides functions to create SQLAlchemy async engines and session factories
with proper configuration based on database type.

Uses the engine abstraction layer to provide database-specific optimizations.
"""

import logging

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from bento.infrastructure.database.config import DatabaseConfig
from bento.infrastructure.database.engines.base import get_engine_for_config

logger = logging.getLogger(__name__)


def create_async_engine_from_config(
    config: DatabaseConfig, use_engine_abstraction: bool = True
) -> AsyncEngine:
    """Create an async database engine from configuration.

    This function uses the engine abstraction layer to provide
    database-specific configurations and optimizations.

    Args:
        config: Database configuration
        use_engine_abstraction: Whether to use engine abstraction (default: True)
            Set to False for backward compatibility

    Returns:
        AsyncEngine: Configured async database engine

    Example:
        ```python
        from bento.infrastructure.database import DatabaseConfig, create_async_engine_from_config

        config = DatabaseConfig(url="postgresql+asyncpg://localhost/mydb")
        engine = create_async_engine_from_config(config)
        ```
    """
    if use_engine_abstraction:
        # Use engine abstraction for database-specific configuration
        db_engine = get_engine_for_config(config)

        # Get database-specific settings
        connect_args = db_engine.get_connect_args()
        pool_kwargs = db_engine.get_pool_kwargs() if db_engine.supports_pool else {}
        engine_kwargs = db_engine.get_engine_kwargs()

        logger.info(f"Creating {config.database_type} engine using {db_engine.__class__.__name__}")

        # Create engine with database-specific configuration
        engine = create_async_engine(
            config.url,
            connect_args=connect_args,
            **pool_kwargs,
            **engine_kwargs,
        )
    else:
        # Legacy mode: Simple configuration without abstraction
        logger.warning("Using legacy engine configuration (consider enabling engine abstraction)")
        engine = create_async_engine(
            config.url,
            echo=config.echo,
        )

    logger.info(f"Database engine created for {config.database_type}")
    return engine


def create_async_session_factory(
    engine: AsyncEngine,
    *,
    expire_on_commit: bool = False,
    autoflush: bool = False,
    autocommit: bool = False,
) -> async_sessionmaker[AsyncSession]:
    """Create an async session factory.

    The session factory is used to create new database sessions.
    Default configuration is optimized for use with the Unit of Work pattern:
    - expire_on_commit=False: Keep objects accessible after commit
    - autoflush=False: Manual control over flush timing
    - autocommit=False: Explicit transaction control

    Args:
        engine: Async database engine
        expire_on_commit: Whether to expire all instances after commit
        autoflush: Whether to automatically flush before queries
        autocommit: Whether to automatically commit after operations

    Returns:
        async_sessionmaker: Factory for creating async sessions

    Example:
        ```python
        engine = create_async_engine_from_config(config)
        session_factory = create_async_session_factory(engine)

        # Create a session
        async with session_factory() as session:
            # Use session
            pass
        ```
    """
    factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=expire_on_commit,
        autoflush=autoflush,
        autocommit=autocommit,
    )

    logger.debug(
        f"Session factory created with expire_on_commit={expire_on_commit}, "
        f"autoflush={autoflush}, autocommit={autocommit}"
    )

    return factory


def create_engine_and_session_factory(
    config: DatabaseConfig,
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """Convenience function to create both engine and session factory.

    Args:
        config: Database configuration

    Returns:
        Tuple of (engine, session_factory)

    Example:
        ```python
        from bento.infrastructure.database import DatabaseConfig, create_engine_and_session_factory

        config = DatabaseConfig()
        engine, session_factory = create_engine_and_session_factory(config)
        ```
    """
    engine = create_async_engine_from_config(config)
    session_factory = create_async_session_factory(engine)
    return engine, session_factory
