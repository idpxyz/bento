"""PostgreSQL database engine configuration.

This module provides PostgreSQL-specific configurations and optimizations.
"""

from typing import Any

from bento.infrastructure.database.engines.base import DatabaseEngine


class PostgreSQLEngine(DatabaseEngine):
    """PostgreSQL-specific database engine configuration.

    Provides optimized settings for PostgreSQL/asyncpg connections:
    - Connection pooling with pre-ping health checks
    - Prepared statement caching
    - Server-side cursor support
    - JSONB column type support
    """

    def get_connect_args(self) -> dict[str, Any]:
        """Get PostgreSQL-specific connection arguments.

        Returns:
            Dictionary of connection arguments including:
            - timeout: Connection timeout
            - command_timeout: Query execution timeout
            - server_settings: PostgreSQL server parameters
        """
        connect_args: dict[str, Any] = {}

        if self.config.connect_timeout:
            connect_args["timeout"] = self.config.connect_timeout

        if self.config.command_timeout:
            connect_args["command_timeout"] = self.config.command_timeout

        # PostgreSQL server settings for better performance
        connect_args["server_settings"] = {
            "application_name": "bento_app",
            "jit": "off",  # Disable JIT compilation for simpler queries
        }

        return connect_args

    def get_pool_kwargs(self) -> dict[str, Any]:
        """Get PostgreSQL connection pool configuration.

        Returns:
            Dictionary with pool settings:
            - pool_size: Base pool size
            - max_overflow: Additional connections allowed
            - pool_timeout: Time to wait for available connection
            - pool_recycle: Time before recycling connections
            - pool_pre_ping: Health check before using connection
        """
        return {
            "pool_size": self.config.pool_size,
            "max_overflow": self.config.max_overflow,
            "pool_timeout": self.config.pool_timeout,
            "pool_recycle": self.config.pool_recycle,
            "pool_pre_ping": self.config.pool_pre_ping,
        }

    @property
    def supports_pool(self) -> bool:
        """PostgreSQL supports connection pooling.

        Returns:
            True
        """
        return True

    @property
    def json_column_type(self) -> str:
        """PostgreSQL supports JSONB for better performance.

        Returns:
            'JSONB'
        """
        return "JSONB"

    def get_engine_kwargs(self) -> dict[str, Any]:
        """Get additional PostgreSQL engine arguments.

        Returns:
            Dictionary with:
            - echo: SQL logging
            - pool_use_lifo: Use LIFO for connection pool (better for most cases)
            - isolation_level: Default transaction isolation level
        """
        kwargs = super().get_engine_kwargs()

        # Use LIFO (Last-In-First-Out) for connection pool
        # This tends to reuse recent connections and allows unused ones to close
        kwargs["pool_use_lifo"] = True

        return kwargs
