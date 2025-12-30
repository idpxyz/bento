"""API health check tests."""

import pytest
from fastapi import FastAPI
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(app: FastAPI, client: AsyncClient):
    """Test health check endpoint.

    Args:
        app: FastAPI application
        client: HTTP client
    """
    response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_openapi_docs(app: FastAPI, client: AsyncClient):
    """Test OpenAPI documentation endpoint.

    Args:
        app: FastAPI application
        client: HTTP client
    """
    response = await client.get("/docs")

    # Should redirect or return docs
    assert response.status_code in [200, 307]


@pytest.mark.asyncio
async def test_openapi_json(app: FastAPI, client: AsyncClient):
    """Test OpenAPI JSON schema endpoint.

    Args:
        app: FastAPI application
        client: HTTP client
    """
    response = await client.get("/openapi.json")

    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data
    assert data["info"]["title"] == "E-commerce API"
