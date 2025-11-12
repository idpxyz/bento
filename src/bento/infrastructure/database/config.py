"""Database configuration management.

This module provides a Pydantic-based configuration model for database connections,
supporting environment variables and multiple database types (PostgreSQL, MySQL, SQLite).
"""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseSettings):
    """Database configuration with environment variable support.

    Supports configuration via environment variables with `DB_` prefix.

    Example:
        ```python
        # From environment variables
        # export DB_URL="postgresql+asyncpg://user:pass@localhost/db"
        # export DB_POOL_SIZE=20
        # export DB_ECHO=true

        config = DatabaseConfig()
        ```

        ```python
        # Direct instantiation
        config = DatabaseConfig(
            url="sqlite+aiosqlite:///./bento.db",
            pool_size=10,
        )
        ```

    Attributes:
        url: Database connection URL
        echo: Whether to log SQL statements
        pool_size: Maximum number of connections in the pool
        max_overflow: Maximum number of connections that can be created beyond pool_size
        pool_timeout: Seconds to wait before giving up on getting a connection from the pool
        pool_recycle: Seconds after which to recycle connections (-1 to disable)
        pool_pre_ping: Enable connection health checks before using
        connect_timeout: Timeout for establishing connections
        command_timeout: Timeout for executing commands (None for no timeout)
    """

    model_config = SettingsConfigDict(
        env_prefix="DB_",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Basic connection settings
    url: str = Field(
        default="sqlite+aiosqlite:///./bento.db",
        description="Database connection URL (e.g., postgresql+asyncpg://user:pass@host/db)",
    )
    echo: bool = Field(
        default=False,
        description="Log all SQL statements to stdout (useful for debugging)",
    )

    # Connection pool settings
    pool_size: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Number of connections to maintain in the pool",
    )
    max_overflow: int = Field(
        default=10,
        ge=0,
        le=100,
        description="Maximum number of connections that can be created beyond pool_size",
    )
    pool_timeout: int = Field(
        default=30,
        ge=1,
        description="Seconds to wait before giving up on getting a connection",
    )
    pool_recycle: int = Field(
        default=3600,
        ge=-1,
        description="Seconds after which to recycle connections (-1 to disable)",
    )
    pool_pre_ping: bool = Field(
        default=True,
        description="Enable connection health check before using",
    )

    # Performance settings
    connect_timeout: int = Field(
        default=10,
        ge=1,
        description="Timeout in seconds for establishing database connection",
    )
    command_timeout: int | None = Field(
        default=None,
        description="Timeout in seconds for executing commands (None for no timeout)",
    )

    @property
    def is_sqlite(self) -> bool:
        """Check if the database is SQLite.

        Returns:
            True if using SQLite, False otherwise
        """
        return self.url.startswith("sqlite")

    @property
    def is_postgres(self) -> bool:
        """Check if the database is PostgreSQL.

        Returns:
            True if using PostgreSQL, False otherwise
        """
        return "postgres" in self.url.lower()

    @property
    def is_mysql(self) -> bool:
        """Check if the database is MySQL.

        Returns:
            True if using MySQL, False otherwise
        """
        return "mysql" in self.url.lower()

    @property
    def database_type(self) -> Literal["sqlite", "postgres", "mysql", "unknown"]:
        """Get the database type.

        Returns:
            Database type as string
        """
        if self.is_sqlite:
            return "sqlite"
        elif self.is_postgres:
            return "postgres"
        elif self.is_mysql:
            return "mysql"
        else:
            return "unknown"


def get_database_config(**kwargs) -> DatabaseConfig:
    """Convenience function to get database configuration.

    This function loads configuration from environment variables
    and allows overriding with keyword arguments.

    Args:
        **kwargs: Optional keyword arguments to override configuration

    Returns:
        DatabaseConfig instance

    Example:
        ```python
        # Load from environment
        config = get_database_config()

        # Override specific settings
        config = get_database_config(
            url="postgresql+asyncpg://localhost/mydb",
            pool_size=20,
        )
        ```
    """
    return DatabaseConfig(**kwargs)
