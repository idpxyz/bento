"""Base database engine configuration.

This module provides an abstract base class for database-specific configurations.
Each database type (PostgreSQL, MySQL, SQLite) can provide its own implementation.
"""

from abc import ABC, abstractmethod
from typing import Any

from bento.infrastructure.database.config import DatabaseConfig


class DatabaseEngine(ABC):
    """Abstract base class for database engine configurations.

    Each database type should subclass this and provide:
    - Connection arguments
    - Pool configuration
    - Database-specific optimizations
    """

    def __init__(self, config: DatabaseConfig):
        """Initialize database engine.

        Args:
            config: Database configuration
        """
        self.config = config

    @abstractmethod
    def get_connect_args(self) -> dict[str, Any]:
        """Get database-specific connection arguments.

        Returns:
            Dictionary of connection arguments for SQLAlchemy
        """
        pass

    @abstractmethod
    def get_pool_kwargs(self) -> dict[str, Any]:
        """Get database-specific connection pool configuration.

        Returns:
            Dictionary of pool configuration for SQLAlchemy
        """
        pass

    def get_engine_kwargs(self) -> dict[str, Any]:
        """Get additional engine creation arguments.

        Returns:
            Dictionary of engine kwargs
        """
        return {
            "echo": self.config.echo,
        }

    @property
    @abstractmethod
    def supports_pool(self) -> bool:
        """Check if this database supports connection pooling.

        Returns:
            True if pooling is supported
        """
        pass

    @property
    def json_column_type(self) -> str:
        """Get the appropriate JSON column type for this database.

        Returns:
            'JSON' or 'JSONB' depending on database support
        """
        return "JSON"


def get_engine_for_config(config: DatabaseConfig) -> DatabaseEngine:
    """Factory function to get appropriate engine for configuration.

    Args:
        config: Database configuration

    Returns:
        DatabaseEngine instance for the database type

    Example:
        ```python
        config = DatabaseConfig(url="postgresql+asyncpg://localhost/db")
        engine = get_engine_for_config(config)
        connect_args = engine.get_connect_args()
        ```
    """
    if config.is_postgres:
        from bento.infrastructure.database.engines.postgres import PostgreSQLEngine

        return PostgreSQLEngine(config)
    elif config.is_sqlite:
        from bento.infrastructure.database.engines.sqlite import SQLiteEngine

        return SQLiteEngine(config)
    elif config.is_mysql:
        # MySQL support to be implemented
        raise NotImplementedError("MySQL support not yet implemented")
    else:
        # Default to a generic engine
        raise ValueError(f"Unsupported database type: {config.database_type}")
