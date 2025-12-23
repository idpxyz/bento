"""Pytest Configuration and Fixtures"""

import asyncio
import sys
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest

# Import Base from Bento Framework
from bento.persistence import Base
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# Add application to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import all PO models to register them with Base.metadata
# Import Base to create all tables

from contexts.catalog.infrastructure.models.category_po import CategoryPO  # noqa: F401
from contexts.catalog.infrastructure.models.product_po import ProductPO  # noqa: F401
from contexts.identity.infrastructure.models.user_po import UserPO  # noqa: F401
from contexts.ordering.infrastructure.models.order_po import OrderPO  # noqa: F401
from contexts.ordering.infrastructure.models.orderitem_po import OrderItemPO  # noqa: F401

# Import OutboxRecord to create outbox table for e2e tests
from bento.persistence.outbox.record import OutboxRecord  # noqa: F401

# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_engine():
    """Create a test database engine with all tables"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Clean up
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session"""
    async_session = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture(scope="function")
def test_app():
    """Create a test FastAPI app with test database"""
    import asyncio

    from fastapi.testclient import TestClient
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from main import app
    from shared.infrastructure.dependencies import get_db_session

    # Create test engine and tables
    test_engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create all tables synchronously
    async def setup_db():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(setup_db())

    # Create session factory
    test_session_factory = async_sessionmaker(test_engine, expire_on_commit=False)

    async def override_get_db_session():
        """Override session dependency for testing"""
        async with test_session_factory() as session:
            yield session

    # Override dependency
    app.dependency_overrides[get_db_session] = override_get_db_session

    yield TestClient(app)

    # Clean up
    async def teardown_db():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await test_engine.dispose()

    asyncio.run(teardown_db())
    app.dependency_overrides.clear()


# TODO: Add more fixtures as needed
# Example:
# @pytest.fixture
# def sample_user():
#     return User(id="test-123", name="Test User", email="test@example.com")
#
# @pytest.fixture
# async def user_repository(db_session):
#     return UserRepository(session=db_session, actor="test")
