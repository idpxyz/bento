"""Kubernetes based service discovery."""

from __future__ import annotations

import logging

from bento.application.ports.service_discovery import (
    ServiceDiscovery,
    ServiceInstance,
)

logger = logging.getLogger(__name__)


class KubernetesServiceDiscovery(ServiceDiscovery):
    """Service discovery using Kubernetes DNS.

    In Kubernetes, services are automatically discoverable via DNS.
    Service DNS format: {service-name}.{namespace}.svc.cluster.local

    Example:
        ```python
        discovery = KubernetesServiceDiscovery(namespace="default")
        instance = await discovery.discover("catalog-service")
        # Returns ServiceInstance for catalog-service.default.svc.cluster.local:8000
        ```
    """

    def __init__(
        self,
        namespace: str = "default",
        suffix: str = "svc.cluster.local",
        default_port: int = 8000,
    ):
        """Initialize Kubernetes service discovery.

        Args:
            namespace: Kubernetes namespace
            suffix: Kubernetes service suffix
            default_port: Default port for services
        """
        self.namespace = namespace
        self.suffix = suffix
        self.default_port = default_port

    async def discover(
        self, service_name: str, strategy: str = "round_robin"
    ) -> ServiceInstance:
        """Discover service using Kubernetes DNS."""
        dns_name = f"{service_name}.{self.namespace}.{self.suffix}"

        return ServiceInstance(
            service_name=service_name,
            host=dns_name,
            port=self.default_port,
            scheme="http",
        )

    async def discover_all(self, service_name: str) -> list[ServiceInstance]:
        """Discover all instances (Kubernetes handles this via DNS)."""
        return [await self.discover(service_name)]

    async def register(
        self,
        service_name: str,
        host: str,
        port: int,
        metadata: dict | None = None,
    ) -> None:
        """Not needed in Kubernetes (automatic via Service)."""
        logger.debug(
            f"Service registration not needed in Kubernetes: {service_name}"
        )

    async def deregister(
        self, service_name: str, host: str, port: int
    ) -> None:
        """Not needed in Kubernetes."""
        logger.debug(
            f"Service deregistration not needed in Kubernetes: {service_name}"
        )

    async def health_check(
        self, service_name: str, host: str, port: int
    ) -> bool:
        """Kubernetes handles health checks via liveness/readiness probes."""
        return True
