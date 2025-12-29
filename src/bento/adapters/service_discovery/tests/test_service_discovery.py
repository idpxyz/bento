"""Unit tests for service discovery."""

from __future__ import annotations

import pytest

from bento.adapters.service_discovery.cached import CachedServiceDiscovery
from bento.adapters.service_discovery.env import EnvServiceDiscovery
from bento.adapters.service_discovery.kubernetes import KubernetesServiceDiscovery
from bento.application.ports.service_discovery import (
    ServiceDiscovery,
    ServiceInstance,
    ServiceNotFoundError,
)


class MockServiceDiscovery(ServiceDiscovery):
    """Mock service discovery for testing."""

    def __init__(self, instances: dict[str, list[ServiceInstance]] | None = None):
        """Initialize mock discovery.

        Args:
            instances: Dictionary mapping service names to instances
        """
        self.instances = instances or {}
        self.registered_services: list[tuple[str, str, int]] = []
        self.deregistered_services: list[tuple[str, str, int]] = []

    async def discover(
        self, service_name: str, strategy: str = "round_robin"
    ) -> ServiceInstance:
        """Discover service."""
        instances = await self.discover_all(service_name)
        if not instances:
            raise ServiceNotFoundError(f"Service {service_name} not found")
        return instances[0]

    async def discover_all(self, service_name: str) -> list[ServiceInstance]:
        """Discover all instances."""
        return self.instances.get(service_name, [])

    async def register(
        self,
        service_name: str,
        host: str,
        port: int,
        metadata: dict | None = None,
    ) -> None:
        """Register service."""
        self.registered_services.append((service_name, host, port))

    async def deregister(
        self, service_name: str, host: str, port: int
    ) -> None:
        """Deregister service."""
        self.deregistered_services.append((service_name, host, port))

    async def health_check(
        self, service_name: str, host: str, port: int
    ) -> bool:
        """Check health."""
        instances = await self.discover_all(service_name)
        for instance in instances:
            if instance.host == host and instance.port == port:
                return True
        return False


@pytest.mark.asyncio
async def test_env_service_discovery(monkeypatch):
    """Test environment variable based service discovery."""
    monkeypatch.setenv("SERVICE_CATALOG_SERVICE_URL", "http://catalog-service:8002")

    discovery = EnvServiceDiscovery()
    instance = await discovery.discover("catalog-service")

    assert instance.service_name == "catalog-service"
    assert instance.host == "catalog-service"
    assert instance.port == 8002
    assert instance.url == "http://catalog-service:8002"


@pytest.mark.asyncio
async def test_env_service_discovery_not_found(monkeypatch):
    """Test service not found in environment."""
    discovery = EnvServiceDiscovery()

    with pytest.raises(ServiceNotFoundError):
        await discovery.discover("unknown-service")


@pytest.mark.asyncio
async def test_kubernetes_service_discovery():
    """Test Kubernetes service discovery."""
    discovery = KubernetesServiceDiscovery(namespace="default")
    instance = await discovery.discover("catalog-service")

    assert instance.service_name == "catalog-service"
    assert instance.host == "catalog-service.default.svc.cluster.local"
    assert instance.port == 8000


@pytest.mark.asyncio
async def test_cached_service_discovery():
    """Test cached service discovery."""
    mock_discovery = MockServiceDiscovery(
        instances={
            "catalog-service": [
                ServiceInstance(
                    service_name="catalog-service",
                    host="catalog-1",
                    port=8002,
                )
            ]
        }
    )

    cached_discovery = CachedServiceDiscovery(mock_discovery, ttl=300)

    # First call should hit underlying discovery
    instance1 = await cached_discovery.discover("catalog-service")
    assert instance1.host == "catalog-1"

    # Second call should hit cache
    instance2 = await cached_discovery.discover("catalog-service")
    assert instance2.host == "catalog-1"

    # Clear cache
    cached_discovery.clear_cache()

    # Next call should hit underlying discovery again
    instance3 = await cached_discovery.discover("catalog-service")
    assert instance3.host == "catalog-1"


@pytest.mark.asyncio
async def test_cached_service_discovery_invalidation():
    """Test cache invalidation on register/deregister."""
    mock_discovery = MockServiceDiscovery(
        instances={
            "catalog-service": [
                ServiceInstance(
                    service_name="catalog-service",
                    host="catalog-1",
                    port=8002,
                )
            ]
        }
    )

    cached_discovery = CachedServiceDiscovery(mock_discovery, ttl=300)

    # Populate cache
    await cached_discovery.discover("catalog-service")

    # Register should invalidate cache
    await cached_discovery.register("catalog-service", "catalog-2", 8002)
    assert ("catalog-service", "catalog-2", 8002) in mock_discovery.registered_services

    # Deregister should invalidate cache
    await cached_discovery.deregister("catalog-service", "catalog-1", 8002)
    assert ("catalog-service", "catalog-1", 8002) in mock_discovery.deregistered_services


@pytest.mark.asyncio
async def test_service_instance_url():
    """Test ServiceInstance URL generation."""
    instance = ServiceInstance(
        service_name="catalog-service",
        host="localhost",
        port=8002,
        scheme="http",
    )

    assert instance.url == "http://localhost:8002"

    instance_https = ServiceInstance(
        service_name="catalog-service",
        host="example.com",
        port=443,
        scheme="https",
    )

    assert instance_https.url == "https://example.com:443"
