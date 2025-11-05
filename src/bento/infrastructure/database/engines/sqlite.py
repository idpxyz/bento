"""SQLite database engine configuration.

This module provides SQLite-specific configurations and optimizations.
"""

from typing import Any

from bento.infrastructure.database.engines.base import DatabaseEngine


class SQLiteEngine(DatabaseEngine):
    """SQLite-specific database engine configuration.

    Provides optimized settings for SQLite/aiosqlite connections:
    - Thread safety configuration
    - Timeout settings
    - No connection pooling (SQLite doesn't benefit from it)
    - JSON column type (not JSONB)
    """

    def get_connect_args(self) -> dict[str, Any]:
        """Get SQLite-specific connection arguments.

        Returns:
            Dictionary of connection arguments including:
            - check_same_thread: Disabled for async operations
            - timeout: Database lock timeout
            - cached_statements: Number of statements to cache
        """
        connect_args = {
            # Allow SQLite to be used from multiple threads (required for async)
            "check_same_thread": False,
            # Timeout for waiting on locked database
            "timeout": float(self.config.connect_timeout),
            # Cache prepared statements for better performance
            "cached_statements": 100,
        }

        return connect_args

    def get_pool_kwargs(self) -> dict[str, Any]:
        """Get SQLite pool configuration.

        SQLite doesn't benefit from connection pooling in the traditional sense,
        so we return minimal pool settings.

        Returns:
            Empty dictionary (no pooling for SQLite)
        """
        # SQLite doesn't use connection pooling
        # The pool is managed internally by SQLAlchemy's NullPool
        return {}

    @property
    def supports_pool(self) -> bool:
        """SQLite doesn't support traditional connection pooling.

        Returns:
            False
        """
        return False

    @property
    def json_column_type(self) -> str:
        """SQLite only supports JSON (not JSONB).

        Returns:
            'JSON'
        """
        return "JSON"

    def get_engine_kwargs(self) -> dict[str, Any]:
        """Get additional SQLite engine arguments.

        Returns:
            Dictionary with:
            - echo: SQL logging
            - poolclass: NullPool (no connection pooling)
        """
        from sqlalchemy.pool import NullPool

        kwargs = super().get_engine_kwargs()

        # Use NullPool for SQLite (no connection pooling)
        # Each connection is created on demand and closed immediately
        kwargs["poolclass"] = NullPool

        return kwargs
