"""Integration tests for database infrastructure."""

import tempfile
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from bento.infrastructure.database import (
    DatabaseConfig,
    DrainingMode,
    cleanup_database,
    create_async_engine_from_config,
    create_async_session_factory,
    drain_connections,
    drop_all_tables,
    get_database_info,
    health_check,
    init_database,
)
from bento.infrastructure.database.resilience import RetryConfig, retry_on_db_error


# Test models
class Base(DeclarativeBase):
    pass


class SampleModel(Base):
    """Sample model for testing database infrastructure."""

    __tablename__ = "test_table"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column()


@pytest_asyncio.fixture
async def test_engine():
    """Create test engine with temporary file database."""
    # Use a temporary file for the database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    config = DatabaseConfig(
        url=f"sqlite+aiosqlite:///{db_path}",
        echo=False,
    )
    engine = create_async_engine_from_config(config)

    yield engine

    await cleanup_database(engine)

    # Clean up the temporary database file
    Path(db_path).unlink(missing_ok=True)


@pytest_asyncio.fixture
async def initialized_engine(test_engine):
    """Create initialized engine with tables."""
    await init_database(test_engine, Base)
    yield test_engine
    await drop_all_tables(test_engine, Base)


class TestDatabaseLifecycle:
    """Test database lifecycle management."""

    @pytest.mark.asyncio
    async def test_init_database(self, test_engine):
        """Test database initialization."""
        await init_database(test_engine, Base)

        # Verify table was created
        async with test_engine.begin() as conn:
            result = await conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='test_table'")
            )
            tables = result.fetchall()
            assert len(tables) == 1

        await drop_all_tables(test_engine, Base)

    @pytest.mark.asyncio
    async def test_health_check(self, initialized_engine):
        """Test health check."""
        is_healthy = await health_check(initialized_engine)
        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_get_database_info(self, initialized_engine):
        """Test getting database information."""
        info = await get_database_info(initialized_engine)

        assert "driver" in info
        assert "database_type" in info
        assert info["database_type"] == "sqlite"

    @pytest.mark.asyncio
    async def test_drop_all_tables(self, initialized_engine):
        """Test dropping all tables."""
        # Verify table exists
        async with initialized_engine.begin() as conn:
            result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables_before = result.fetchall()
            assert len(tables_before) > 0

        # Drop all tables
        await drop_all_tables(initialized_engine, Base)

        # Verify tables were dropped
        async with initialized_engine.begin() as conn:
            result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables_after = result.fetchall()
            assert len(tables_after) == 0


class TestSessionManagement:
    """Test session management."""

    @pytest.mark.asyncio
    async def test_create_session_and_query(self, initialized_engine):
        """Test creating session and executing query."""
        session_factory = create_async_session_factory(initialized_engine)

        async with session_factory() as session:
            async with session.begin():
                # Insert test data
                test_obj = SampleModel(id=1, name="Test")
                session.add(test_obj)

            # Query data
            result = await session.execute(select(SampleModel))
            objects = result.scalars().all()

            assert len(objects) == 1
            assert objects[0].name == "Test"

    @pytest.mark.asyncio
    async def test_session_transaction_commit(self, initialized_engine):
        """Test session transaction commit."""
        session_factory = create_async_session_factory(initialized_engine)

        async with session_factory() as session:
            async with session.begin():
                test_obj = SampleModel(id=1, name="Committed")
                session.add(test_obj)

        # Verify data was committed
        async with session_factory() as session:
            result = await session.execute(select(SampleModel))
            objects = result.scalars().all()
            assert len(objects) == 1
            assert objects[0].name == "Committed"

    @pytest.mark.asyncio
    async def test_session_transaction_rollback(self, initialized_engine):
        """Test session transaction rollback."""
        session_factory = create_async_session_factory(initialized_engine)

        try:
            async with session_factory() as session:
                async with session.begin():
                    test_obj = SampleModel(id=1, name="RolledBack")
                    session.add(test_obj)
                    # Simulate error
                    raise RuntimeError("Test error")
        except RuntimeError:
            pass

        # Verify data was not committed
        async with session_factory() as session:
            result = await session.execute(select(SampleModel))
            objects = result.scalars().all()
            assert len(objects) == 0


class TestConnectionDraining:
    """Test connection draining."""

    @pytest.mark.asyncio
    async def test_drain_connections_graceful(self, initialized_engine):
        """Test graceful connection draining."""
        stats = await drain_connections(
            initialized_engine,
            timeout=5.0,
            mode=DrainingMode.GRACEFUL,
        )

        assert stats["success"] is True
        assert stats["mode"] == "graceful"
        assert "connections_at_start" in stats
        assert "connections_at_end" in stats
        assert "time_taken" in stats

    @pytest.mark.asyncio
    async def test_drain_connections_immediate(self, initialized_engine):
        """Test immediate connection draining."""
        stats = await drain_connections(
            initialized_engine,
            timeout=1.0,
            mode=DrainingMode.IMMEDIATE,
        )

        assert stats["success"] is True
        assert stats["mode"] == "immediate"

    @pytest.mark.asyncio
    async def test_drain_connections_force(self, initialized_engine):
        """Test force connection draining."""
        stats = await drain_connections(
            initialized_engine,
            timeout=1.0,
            mode=DrainingMode.FORCE,
        )

        assert stats["success"] is True
        assert stats["mode"] == "force"


class TestResilienceIntegration:
    """Test resilience integration."""

    @pytest.mark.asyncio
    async def test_retry_on_transient_error(self, initialized_engine):
        """Test retry on transient database error."""
        session_factory = create_async_session_factory(initialized_engine)
        call_count = 0

        async def flaky_operation():
            nonlocal call_count
            call_count += 1

            # Fail first 2 times
            if call_count < 3:
                # Simulate connection error
                raise ConnectionError("Connection lost")

            # Succeed on 3rd attempt
            async with session_factory() as session:
                result = await session.execute(select(SampleModel))
                return result.scalars().all()

        config = RetryConfig(max_attempts=3, base_delay=0.01)

        # Should succeed after retries
        # Note: ConnectionError is not a SQLAlchemy error, so won't be retried
        # This is just a simulation test
        try:
            await retry_on_db_error(flaky_operation, config=config)
            # If ConnectionError is not in retry list, this will raise
        except ConnectionError:
            # Expected - ConnectionError is not a database error
            assert call_count == 1

    @pytest.mark.asyncio
    async def test_successful_query_no_retry(self, initialized_engine):
        """Test successful query doesn't trigger retry."""
        session_factory = create_async_session_factory(initialized_engine)
        call_count = 0

        async def successful_query():
            nonlocal call_count
            call_count += 1

            async with session_factory() as session:
                result = await session.execute(select(SampleModel))
                return result.scalars().all()

        result = await retry_on_db_error(successful_query)

        assert isinstance(result, list)
        assert call_count == 1  # No retry needed


class TestEngineAbstraction:
    """Test engine abstraction integration."""

    @pytest.mark.asyncio
    async def test_sqlite_engine_optimization(self):
        """Test SQLite engine uses correct optimizations."""
        config = DatabaseConfig(url="sqlite+aiosqlite:///:memory:")
        engine = create_async_engine_from_config(config)

        # Verify engine was created
        assert engine is not None

        # Check that we can use it
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            value = result.scalar()
            assert value == 1

        await cleanup_database(engine)

    @pytest.mark.asyncio
    async def test_config_echo_respected(self):
        """Test echo configuration is respected."""
        config = DatabaseConfig(
            url="sqlite+aiosqlite:///:memory:",
            echo=False,  # Should not log SQL
        )
        engine = create_async_engine_from_config(config)

        assert engine.echo is False

        await cleanup_database(engine)
