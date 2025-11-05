"""Unit tests for database configuration."""

import pytest
from pydantic import ValidationError

from bento.infrastructure.database import DatabaseConfig


class TestDatabaseConfig:
    """Test DatabaseConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = DatabaseConfig()

        assert config.url == "sqlite+aiosqlite:///./app.db"
        assert config.pool_size == 5
        assert config.max_overflow == 10
        assert config.pool_timeout == 30.0
        assert config.pool_recycle == 3600
        assert config.pool_pre_ping is True
        assert config.connect_timeout == 10.0
        assert config.command_timeout is None  # Optional, not set by default
        assert config.echo is False

    def test_custom_config(self):
        """Test custom configuration."""
        config = DatabaseConfig(
            url="postgresql+asyncpg://localhost/test",
            pool_size=20,
            max_overflow=30,
            echo=True,
        )

        assert config.url == "postgresql+asyncpg://localhost/test"
        assert config.pool_size == 20
        assert config.max_overflow == 30
        assert config.echo is True

    def test_database_type_detection_postgresql(self):
        """Test PostgreSQL detection."""
        config = DatabaseConfig(url="postgresql+asyncpg://localhost/db")

        assert config.database_type in ("postgres", "postgresql")  # Both are valid
        assert config.is_postgres is True
        assert config.is_sqlite is False
        assert config.is_mysql is False

    def test_database_type_detection_sqlite(self):
        """Test SQLite detection."""
        config = DatabaseConfig(url="sqlite+aiosqlite:///test.db")

        assert config.database_type == "sqlite"
        assert config.is_sqlite is True
        assert config.is_postgres is False
        assert config.is_mysql is False

    def test_database_type_detection_mysql(self):
        """Test MySQL detection."""
        config = DatabaseConfig(url="mysql+aiomysql://localhost/db")

        assert config.database_type == "mysql"
        assert config.is_mysql is True
        assert config.is_postgres is False
        assert config.is_sqlite is False

    def test_database_type_detection_unknown(self):
        """Test unknown database type."""
        config = DatabaseConfig(url="oracle://localhost/db")

        assert config.database_type == "unknown"
        assert config.is_postgres is False
        assert config.is_sqlite is False
        assert config.is_mysql is False

    def test_config_validation(self):
        """Test configuration validation."""
        # Valid config
        config = DatabaseConfig(pool_size=10, max_overflow=20)
        assert config.pool_size == 10

        # Invalid pool_size (negative)
        with pytest.raises(ValidationError):
            DatabaseConfig(pool_size=-1)

        # Invalid pool_timeout (negative)
        with pytest.raises(ValidationError):
            DatabaseConfig(pool_timeout=-1)

    def test_config_from_env(self, monkeypatch):
        """Test configuration from environment variables."""
        monkeypatch.setenv("DB_URL", "postgresql://localhost/testdb")
        monkeypatch.setenv("DB_POOL_SIZE", "15")
        monkeypatch.setenv("DB_ECHO", "true")

        config = DatabaseConfig()

        assert "postgresql" in config.url
        assert config.pool_size == 15
        assert config.echo is True
