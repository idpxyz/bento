"""Tests for order API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test health check endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_create_order(client: AsyncClient):
    """Test creating an order."""
    # Note: This will fail until we properly wire up the UoW in the app
    # For now, it's a placeholder showing the test structure
    pytest.skip("Placeholder until API wiring is implemented")

    # This test is a placeholder - actual implementation depends on
    # properly setting up the database and dependency injection
    # response = await client.post("/api/orders", json=order_data)
    # assert response.status_code == 200


@pytest.mark.asyncio
async def test_openapi_docs(client: AsyncClient):
    """Test that OpenAPI documentation is available."""
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data
    assert data["info"]["title"] == "E-commerce API"
