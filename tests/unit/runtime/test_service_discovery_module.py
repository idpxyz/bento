"""Tests for service discovery runtime module integration."""

from __future__ import annotations

import pytest

from bento.adapters.service_discovery.config import (
    ServiceDiscoveryBackend,
    ServiceDiscoveryConfig,
)
from bento.runtime.container import BentoContainer
from bento.runtime.integrations.service_discovery import ServiceDiscoveryModule


@pytest.mark.asyncio
async def test_service_discovery_module_env_backend() -> None:
    config = ServiceDiscoveryConfig(backend=ServiceDiscoveryBackend.ENV)
    module = ServiceDiscoveryModule(config)

    assert module.name == "service_discovery"
    assert module.config.backend == ServiceDiscoveryBackend.ENV

    container = BentoContainer()
    await module.on_register(container)

    discovery = container.get("service.discovery")
    assert discovery is not None
    assert hasattr(discovery, "discover")


@pytest.mark.asyncio
async def test_service_discovery_module_kubernetes_backend() -> None:
    config = ServiceDiscoveryConfig(
        backend=ServiceDiscoveryBackend.KUBERNETES,
        kubernetes_namespace="default",
        kubernetes_service_suffix=".svc.cluster.local",
    )
    module = ServiceDiscoveryModule(config)

    container = BentoContainer()
    await module.on_register(container)

    discovery = container.get("service.discovery")
    assert discovery is not None


@pytest.mark.asyncio
async def test_service_discovery_module_consul_backend() -> None:
    config = ServiceDiscoveryConfig(
        backend=ServiceDiscoveryBackend.CONSUL,
        consul_url="http://consul:8500",
    )
    module = ServiceDiscoveryModule(config)

    container = BentoContainer()
    await module.on_register(container)

    discovery = container.get("service.discovery")
    assert discovery is not None


@pytest.mark.asyncio
async def test_service_discovery_module_unknown_backend() -> None:
    config = ServiceDiscoveryConfig(backend="unknown")  # type: ignore[arg-type]
    module = ServiceDiscoveryModule(config)

    container = BentoContainer()
    with pytest.raises(ValueError, match="Unknown service discovery backend"):
        await module.on_register(container)


@pytest.mark.asyncio
async def test_service_discovery_module_default_config() -> None:
    module = ServiceDiscoveryModule()
    assert module.config is not None
    container = BentoContainer()
    await module.on_register(container)
    discovery = container.get("service.discovery")
    assert discovery is not None


@pytest.mark.asyncio
async def test_service_discovery_module_shutdown() -> None:
    config = ServiceDiscoveryConfig(backend=ServiceDiscoveryBackend.ENV)
    module = ServiceDiscoveryModule(config)

    container = BentoContainer()
    await module.on_register(container)
    await module.on_shutdown(container)
