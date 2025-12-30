"""Service discovery integration with Bento Runtime."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from bento.adapters.service_discovery.cached import CachedServiceDiscovery
from bento.adapters.service_discovery.config import (
    ServiceDiscoveryBackend,
    ServiceDiscoveryConfig,
)
from bento.adapters.service_discovery.consul import ConsulServiceDiscovery
from bento.adapters.service_discovery.env import EnvServiceDiscovery
from bento.adapters.service_discovery.kubernetes import KubernetesServiceDiscovery
from bento.runtime.module import BentoModule

if TYPE_CHECKING:
    from bento.runtime.container import BentoContainer

logger = logging.getLogger(__name__)


class ServiceDiscoveryModule(BentoModule):
    """Service discovery module for Bento Runtime.

    Provides service discovery capabilities based on configured backend.

    Example:
        ```python
        from bento.runtime import RuntimeBuilder
        from bento.adapters.service_discovery import (
            ServiceDiscoveryModule,
            ServiceDiscoveryConfig,
            ServiceDiscoveryBackend,
        )

        runtime = (
            RuntimeBuilder()
            .with_modules(
                ServiceDiscoveryModule(
                    ServiceDiscoveryConfig(
                        backend=ServiceDiscoveryBackend.CONSUL,
                        consul_url="http://localhost:8500",
                    )
                )
            )
            .build_runtime()
        )
        ```
    """

    name = "service_discovery"

    def __init__(self, config: ServiceDiscoveryConfig | None = None):
        """Initialize service discovery module.

        Args:
            config: Service discovery configuration. If None, loads from environment.
        """
        super().__init__()
        self.config = config or ServiceDiscoveryConfig.from_env()

    async def on_register(self, container: BentoContainer) -> None:
        """Register service discovery."""
        logger.info(f"Registering service discovery: {self.config.backend}")

        # Create discovery based on backend
        if self.config.backend == ServiceDiscoveryBackend.ENV:
            discovery = EnvServiceDiscovery()
        elif self.config.backend == ServiceDiscoveryBackend.CONSUL:
            discovery = ConsulServiceDiscovery(
                consul_url=self.config.consul_url or "http://localhost:8500"
            )
        elif self.config.backend == ServiceDiscoveryBackend.KUBERNETES:
            discovery = KubernetesServiceDiscovery(
                namespace=self.config.kubernetes_namespace,
                suffix=self.config.kubernetes_service_suffix,
            )
        else:
            raise ValueError(f"Unknown service discovery backend: {self.config.backend}")

        # Add caching
        discovery = CachedServiceDiscovery(discovery, ttl=self.config.cache_ttl)

        # Register in container
        container.set("service.discovery", discovery)

        logger.info(
            f"Service discovery registered: {self.config.backend} "
            f"(cache_ttl={self.config.cache_ttl}s)"
        )

    async def on_shutdown(self, container: BentoContainer) -> None:
        """Cleanup on shutdown."""
        logger.info("Service discovery module shutting down")
