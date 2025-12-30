"""Environment variable based service discovery."""

from __future__ import annotations

import os
import re
from urllib.parse import urlparse

from bento.application.ports.service_discovery import (
    ServiceDiscovery,
    ServiceInstance,
    ServiceNotFoundError,
)


class EnvServiceDiscovery(ServiceDiscovery):
    """Service discovery using environment variables.

    Expected format:
    SERVICE_CATALOG_SERVICE_URL=http://catalog-service:8002
    SERVICE_ORDER_SERVICE_URL=http://order-service:8003

    Example:
        ```python
        discovery = EnvServiceDiscovery()
        instance = await discovery.discover("catalog-service")
        # Returns ServiceInstance for http://catalog-service:8002
        ```
    """

    async def discover(self, service_name: str, strategy: str = "round_robin") -> ServiceInstance:
        """Discover service from environment variable."""
        normalized_name = re.sub(r"[^A-Z0-9]", "_", service_name.upper())
        env_var = f"SERVICE_{normalized_name}_URL"
        url = os.getenv(env_var)

        if not url:
            raise ServiceNotFoundError(
                f"Service {service_name} not found. Set environment variable: {env_var}"
            )

        # Parse URL
        parsed = urlparse(url)

        return ServiceInstance(
            service_name=service_name,
            host=parsed.hostname or "localhost",
            port=parsed.port or 80,
            scheme=parsed.scheme or "http",
        )

    async def discover_all(self, service_name: str) -> list[ServiceInstance]:
        """Discover all instances (only one in env mode)."""
        return [await self.discover(service_name)]

    async def register(
        self,
        service_name: str,
        host: str,
        port: int,
        metadata: dict | None = None,
    ) -> None:
        """Not supported in env mode."""
        raise NotImplementedError("Registration not supported in env mode")

    async def deregister(self, service_name: str, host: str, port: int) -> None:
        """Not supported in env mode."""
        raise NotImplementedError("Deregistration not supported in env mode")

    async def health_check(self, service_name: str, host: str, port: int) -> bool:
        """Not supported in env mode."""
        return True
