"""Pytest configuration for e-commerce application tests.

Provides fixtures for testing including database, HTTP client, and app instance.
"""

import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from applications.ecommerce.runtime.bootstrap import create_app


@pytest.fixture
async def app() -> FastAPI:
    """Create FastAPI application instance.
    
    Returns:
        FastAPI application
    """
    return create_app()


@pytest.fixture
async def client(app: FastAPI) -> AsyncClient:
    """Create async HTTP client for testing.
    
    Args:
        app: FastAPI application
        
    Yields:
        Async HTTP client
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def db_session() -> AsyncSession:
    """Create test database session.
    
    Uses in-memory SQLite database for testing.
    
    Yields:
        Database session
    """
    # Create in-memory test database
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    # Create tables
    from applications.ecommerce.persistence.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Provide session
    async with async_session() as session:
        yield session
    
    # Cleanup
    await engine.dispose()
