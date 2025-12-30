"""Standalone database utilities for scripts and tests.

This module provides database access for standalone scripts (init_db.py, etc.)
that run outside the BentoRuntime context.

DO NOT use this in production code. Production code should use:
    from shared.infrastructure.dependencies import get_db_session, get_uow

Usage in scripts:
    from shared.infrastructure.standalone_db import get_standalone_engine

    engine = get_standalone_engine()
    # Use engine for migrations, initialization, etc.
"""

from bento.infrastructure.database import create_async_engine_from_config
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from config import settings

# Cached standalone resources
_standalone_engine: AsyncEngine | None = None
_standalone_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_standalone_engine() -> AsyncEngine:
    """Get standalone database engine for scripts.

    WARNING: Only use in standalone scripts, not in production code.

    Returns:
        AsyncEngine instance
    """
    global _standalone_engine

    if _standalone_engine is None:
        db_config = settings.get_database_config()
        _standalone_engine = create_async_engine_from_config(db_config)

    return _standalone_engine


def get_standalone_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get standalone session factory for scripts.

    WARNING: Only use in standalone scripts, not in production code.

    Returns:
        async_sessionmaker instance
    """
    global _standalone_session_factory

    if _standalone_session_factory is None:
        engine = get_standalone_engine()
        _standalone_session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    return _standalone_session_factory


# Backward compatibility aliases
engine = property(lambda self: get_standalone_engine())
session_factory = property(lambda self: get_standalone_session_factory())
