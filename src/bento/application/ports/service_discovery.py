"""Service discovery port (application layer protocol)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ServiceInstance:
    """Service instance information."""

    service_name: str
    host: str
    port: int
    scheme: str = "http"
    metadata: dict | None = None

    @property
    def url(self) -> str:
        """Get service URL."""
        return f"{self.scheme}://{self.host}:{self.port}"


class ServiceNotFoundError(Exception):
    """Raised when service is not found."""

    pass


class ServiceDiscovery(ABC):
    """Service discovery port (application layer protocol).

    Defines the interface for discovering service instances.
    Implementations should handle:
    - Service registration
    - Service discovery
    - Health checking
    - Load balancing

    Example:
        ```python
        service_discovery = container.get("service.discovery")
        instance = await service_discovery.discover("catalog-service")
        client = CatalogClient(base_url=instance.url)
        ```
    """

    @abstractmethod
    async def discover(
        self, service_name: str, strategy: str = "round_robin"
    ) -> ServiceInstance:
        """Discover a service instance.

        Args:
            service_name: Name of the service to discover
            strategy: Load balancing strategy (round_robin, random, etc.)

        Returns:
            ServiceInstance with service details

        Raises:
            ServiceNotFoundError: If service not found
        """
        pass

    @abstractmethod
    async def discover_all(self, service_name: str) -> list[ServiceInstance]:
        """Discover all instances of a service.

        Args:
            service_name: Name of the service

        Returns:
            List of ServiceInstance objects
        """
        pass

    @abstractmethod
    async def register(
        self,
        service_name: str,
        host: str,
        port: int,
        metadata: dict | None = None,
    ) -> None:
        """Register a service instance.

        Args:
            service_name: Name of the service
            host: Host address
            port: Port number
            metadata: Optional metadata
        """
        pass

    @abstractmethod
    async def deregister(
        self, service_name: str, host: str, port: int
    ) -> None:
        """Deregister a service instance.

        Args:
            service_name: Name of the service
            host: Host address
            port: Port number
        """
        pass

    @abstractmethod
    async def health_check(
        self, service_name: str, host: str, port: int
    ) -> bool:
        """Check health of a service instance.

        Args:
            service_name: Name of the service
            host: Host address
            port: Port number

        Returns:
            True if healthy, False otherwise
        """
        pass
