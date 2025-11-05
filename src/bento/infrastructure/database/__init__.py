"""Bento Database Infrastructure.

This module provides a clean, type-safe database infrastructure for Bento applications.
It includes configuration management, session factories, and lifecycle management.

Quick Start:
    ```python
    from bento.infrastructure.database import (
        DatabaseConfig,
        create_async_engine_from_config,
        create_async_session_factory,
        init_database,
        cleanup_database,
    )
    from your_app.models import Base

    # 1. Load configuration (from environment variables)
    config = DatabaseConfig()

    # 2. Create engine and session factory
    engine = create_async_engine_from_config(config)
    session_factory = create_async_session_factory(engine)

    # 3. Initialize database
    await init_database(engine, Base)

    # 4. Use in your application
    async with session_factory() as session:
        # Your database operations
        pass

    # 5. Clean up on shutdown
    await cleanup_database(engine)
    ```

Architecture:
    The database infrastructure is designed to support Bento's hexagonal architecture:

    - Application Layer: Depends on IUnitOfWork interface
    - Persistence Layer: Uses the database infrastructure
    - Infrastructure Layer: Provides the database implementation

    This separation ensures clean dependencies and testability.
"""

# Configuration
from bento.infrastructure.database.config import (
    DatabaseConfig,
    get_database_config,
)

# Draining
from bento.infrastructure.database.draining import (
    ConnectionDrainer,
    DrainingMode,
    drain_connections,
    drain_with_signal_handler,
)

# Lifecycle Management
from bento.infrastructure.database.lifecycle import (
    cleanup_database,
    drop_all_tables,
    get_database_info,
    health_check,
    init_database,
)

# Session Management
from bento.infrastructure.database.session import (
    create_async_engine_from_config,
    create_async_session_factory,
    create_engine_and_session_factory,
)

__all__ = [
    # Configuration
    "DatabaseConfig",
    "get_database_config",
    # Session Management
    "create_async_engine_from_config",
    "create_async_session_factory",
    "create_engine_and_session_factory",
    # Lifecycle Management
    "init_database",
    "cleanup_database",
    "health_check",
    "drop_all_tables",
    "get_database_info",
    # Draining
    "ConnectionDrainer",
    "DrainingMode",
    "drain_connections",
    "drain_with_signal_handler",
]

__version__ = "0.1.0"
