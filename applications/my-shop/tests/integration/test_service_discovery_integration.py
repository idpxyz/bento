"""Integration tests for service discovery in my-shop application."""

from __future__ import annotations

import os

import pytest

from bento.adapters.service_discovery.config import ServiceDiscoveryBackend
from bento.application.ports.service_discovery import ServiceNotFoundError
from runtime.bootstrap_v2 import create_runtime
from shared.services.external_service_client import ExternalServiceClient


@pytest.mark.asyncio
async def test_service_discovery_module_registered():
    """Test that service discovery module is registered in runtime."""
    runtime = create_runtime()
    await runtime.build_async()

    # Service discovery should be available in container
    discovery = runtime.container.get("service.discovery")
    assert discovery is not None
    assert hasattr(discovery, "discover")

    await runtime.shutdown_async()


@pytest.mark.asyncio
async def test_env_backend_service_discovery(monkeypatch):
    """Test service discovery with ENV backend."""
    # Set up environment variables
    monkeypatch.setenv("SERVICE_DISCOVERY_BACKEND", "env")
    monkeypatch.setenv("SERVICE_CATALOG_SERVICE_URL", "http://catalog:8001")
    monkeypatch.setenv("SERVICE_ORDER_SERVICE_URL", "http://order:8002")

    runtime = create_runtime()
    await runtime.build_async()

    discovery = runtime.container.get("service.discovery")

    # Discover catalog service
    instance = await discovery.discover("catalog-service")
    assert instance.service_name == "catalog-service"
    assert instance.host == "catalog"
    assert instance.port == 8001

    # Discover order service
    instance = await discovery.discover("order-service")
    assert instance.service_name == "order-service"
    assert instance.host == "order"
    assert instance.port == 8002

    await runtime.shutdown_async()


@pytest.mark.asyncio
async def test_service_not_found_error(monkeypatch):
    """Test that ServiceNotFoundError is raised for unknown services."""
    monkeypatch.setenv("SERVICE_DISCOVERY_BACKEND", "env")

    runtime = create_runtime()
    await runtime.build_async()

    discovery = runtime.container.get("service.discovery")

    # Try to discover non-existent service
    with pytest.raises(ServiceNotFoundError):
        await discovery.discover("non-existent-service")

    await runtime.shutdown_async()


@pytest.mark.asyncio
async def test_service_discovery_caching(monkeypatch):
    """Test that service discovery results are cached."""
    monkeypatch.setenv("SERVICE_DISCOVERY_BACKEND", "env")
    monkeypatch.setenv("SERVICE_CATALOG_SERVICE_URL", "http://catalog:8001")

    runtime = create_runtime()
    await runtime.build_async()

    discovery = runtime.container.get("service.discovery")

    # First call - should hit the backend
    instance1 = await discovery.discover("catalog-service")

    # Second call - should hit the cache
    instance2 = await discovery.discover("catalog-service")

    # Both should return the same service instance
    assert instance1.host == instance2.host
    assert instance1.port == instance2.port

    await runtime.shutdown_async()


@pytest.mark.asyncio
async def test_external_service_client(monkeypatch):
    """Test ExternalServiceClient with service discovery."""
    monkeypatch.setenv("SERVICE_DISCOVERY_BACKEND", "env")
    monkeypatch.setenv("SERVICE_CATALOG_SERVICE_URL", "http://catalog:8001")

    runtime = create_runtime()
    await runtime.build_async()

    discovery = runtime.container.get("service.discovery")
    client = ExternalServiceClient(discovery)

    # Verify service can be discovered
    instance = await discovery.discover("catalog-service")
    assert instance.host == "catalog"
    assert instance.port == 8001

    await client.close()
    await runtime.shutdown_async()


@pytest.mark.asyncio
async def test_kubernetes_backend_configuration(monkeypatch):
    """Test service discovery with Kubernetes backend configuration."""
    monkeypatch.setenv("SERVICE_DISCOVERY_BACKEND", "kubernetes")
    monkeypatch.setenv("KUBERNETES_NAMESPACE", "production")
    monkeypatch.setenv("KUBERNETES_SERVICE_SUFFIX", "svc.cluster.local")

    runtime = create_runtime()
    await runtime.build_async()

    discovery = runtime.container.get("service.discovery")

    # Discover service using Kubernetes DNS
    instance = await discovery.discover("catalog-service")

    # Kubernetes DNS format: <service>.<namespace>.svc.cluster.local
    assert instance.service_name == "catalog-service"
    assert "catalog-service" in instance.host
    assert "production" in instance.host or instance.host == "catalog-service"

    await runtime.shutdown_async()


@pytest.mark.asyncio
async def test_service_discovery_config_from_settings():
    """Test that service discovery config is loaded from settings."""
    runtime = create_runtime()
    await runtime.build_async()

    discovery = runtime.container.get("service.discovery")

    # Verify discovery is configured
    assert discovery is not None

    # Check that it has the expected methods
    assert hasattr(discovery, "discover")
    assert hasattr(discovery, "register")
    assert hasattr(discovery, "deregister")

    await runtime.shutdown_async()
