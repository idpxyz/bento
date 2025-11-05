"""Unit tests for database engines."""

import pytest

from bento.infrastructure.database import DatabaseConfig
from bento.infrastructure.database.engines import (
    PostgreSQLEngine,
    SQLiteEngine,
    get_engine_for_config,
)


class TestDatabaseEngineFactory:
    """Test database engine factory."""

    def test_get_engine_for_postgres(self):
        """Test getting PostgreSQL engine."""
        config = DatabaseConfig(url="postgresql+asyncpg://localhost/db")
        engine = get_engine_for_config(config)

        assert isinstance(engine, PostgreSQLEngine)
        assert engine.supports_pool is True
        assert engine.json_column_type == "JSONB"

    def test_get_engine_for_sqlite(self):
        """Test getting SQLite engine."""
        config = DatabaseConfig(url="sqlite+aiosqlite:///test.db")
        engine = get_engine_for_config(config)

        assert isinstance(engine, SQLiteEngine)
        assert engine.supports_pool is False
        assert engine.json_column_type == "JSON"

    def test_get_engine_for_mysql_raises(self):
        """Test MySQL not implemented."""
        config = DatabaseConfig(url="mysql+aiomysql://localhost/db")

        with pytest.raises(NotImplementedError, match="MySQL support not yet implemented"):
            get_engine_for_config(config)

    def test_get_engine_for_unknown_raises(self):
        """Test unknown database raises."""
        config = DatabaseConfig(url="oracle://localhost/db")

        with pytest.raises(ValueError, match="Unsupported database type"):
            get_engine_for_config(config)


class TestPostgreSQLEngine:
    """Test PostgreSQL engine."""

    def test_postgres_connect_args(self):
        """Test PostgreSQL connection arguments."""
        config = DatabaseConfig(
            url="postgresql+asyncpg://localhost/db",
            connect_timeout=20,
            command_timeout=120,
        )
        engine = PostgreSQLEngine(config)

        connect_args = engine.get_connect_args()

        assert connect_args["timeout"] == 20.0
        assert connect_args["command_timeout"] == 120.0
        assert "server_settings" in connect_args
        assert connect_args["server_settings"]["application_name"] == "bento_app"
        assert connect_args["server_settings"]["jit"] == "off"

    def test_postgres_pool_kwargs(self):
        """Test PostgreSQL pool configuration."""
        config = DatabaseConfig(
            url="postgresql+asyncpg://localhost/db",
            pool_size=25,
            max_overflow=15,
            pool_timeout=45,
            pool_recycle=7200,
            pool_pre_ping=False,
        )
        engine = PostgreSQLEngine(config)

        pool_kwargs = engine.get_pool_kwargs()

        assert pool_kwargs["pool_size"] == 25
        assert pool_kwargs["max_overflow"] == 15
        assert pool_kwargs["pool_timeout"] == 45
        assert pool_kwargs["pool_recycle"] == 7200
        assert pool_kwargs["pool_pre_ping"] is False

    def test_postgres_supports_pool(self):
        """Test PostgreSQL supports pooling."""
        config = DatabaseConfig(url="postgresql+asyncpg://localhost/db")
        engine = PostgreSQLEngine(config)

        assert engine.supports_pool is True

    def test_postgres_json_column_type(self):
        """Test PostgreSQL uses JSONB."""
        config = DatabaseConfig(url="postgresql+asyncpg://localhost/db")
        engine = PostgreSQLEngine(config)

        assert engine.json_column_type == "JSONB"

    def test_postgres_engine_kwargs(self):
        """Test PostgreSQL engine kwargs."""
        config = DatabaseConfig(url="postgresql+asyncpg://localhost/db", echo=True)
        engine = PostgreSQLEngine(config)

        engine_kwargs = engine.get_engine_kwargs()

        assert engine_kwargs["echo"] is True
        assert engine_kwargs["pool_use_lifo"] is True


class TestSQLiteEngine:
    """Test SQLite engine."""

    def test_sqlite_connect_args(self):
        """Test SQLite connection arguments."""
        config = DatabaseConfig(
            url="sqlite+aiosqlite:///test.db",
            connect_timeout=15,
        )
        engine = SQLiteEngine(config)

        connect_args = engine.get_connect_args()

        assert connect_args["check_same_thread"] is False
        assert connect_args["timeout"] == 15.0
        assert connect_args["cached_statements"] == 100

    def test_sqlite_pool_kwargs(self):
        """Test SQLite pool configuration."""
        config = DatabaseConfig(url="sqlite+aiosqlite:///test.db")
        engine = SQLiteEngine(config)

        pool_kwargs = engine.get_pool_kwargs()

        # SQLite doesn't use connection pooling
        assert pool_kwargs == {}

    def test_sqlite_supports_pool(self):
        """Test SQLite doesn't support traditional pooling."""
        config = DatabaseConfig(url="sqlite+aiosqlite:///test.db")
        engine = SQLiteEngine(config)

        assert engine.supports_pool is False

    def test_sqlite_json_column_type(self):
        """Test SQLite uses JSON."""
        config = DatabaseConfig(url="sqlite+aiosqlite:///test.db")
        engine = SQLiteEngine(config)

        assert engine.json_column_type == "JSON"

    def test_sqlite_engine_kwargs(self):
        """Test SQLite engine kwargs."""
        config = DatabaseConfig(url="sqlite+aiosqlite:///test.db", echo=False)
        engine = SQLiteEngine(config)

        engine_kwargs = engine.get_engine_kwargs()

        assert engine_kwargs["echo"] is False
        assert "poolclass" in engine_kwargs
        # Check that NullPool is used
        from sqlalchemy.pool import NullPool

        assert engine_kwargs["poolclass"] == NullPool
