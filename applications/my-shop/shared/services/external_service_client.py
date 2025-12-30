"""External service client using service discovery.

Demonstrates how to use service discovery for cross-service communication.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from bento.application.ports.service_discovery import ServiceDiscovery

logger = logging.getLogger(__name__)


class ExternalServiceClient:
    """Client for calling external services using service discovery.

    Example:
        ```python
        # In a command handler or query handler
        discovery = container.get("service.discovery")
        client = ExternalServiceClient(discovery)

        # Call another service
        result = await client.call_service(
            service_name="catalog-service",
            path="/api/v1/products",
            method="GET"
        )
        ```
    """

    def __init__(self, discovery: ServiceDiscovery):
        """Initialize client with service discovery.

        Args:
            discovery: Service discovery instance from container
        """
        self.discovery = discovery
        self._http_client = httpx.AsyncClient(timeout=30.0)

    async def call_service(
        self,
        service_name: str,
        path: str,
        method: str = "GET",
        **kwargs,
    ) -> dict:
        """Call an external service using service discovery.

        Args:
            service_name: Name of the service to call (e.g., "catalog-service")
            path: API path (e.g., "/api/v1/products")
            method: HTTP method (GET, POST, PUT, DELETE)
            **kwargs: Additional arguments for httpx request

        Returns:
            Response JSON data

        Raises:
            ServiceNotFoundError: If service cannot be discovered
            httpx.HTTPError: If HTTP request fails
        """
        # Discover service instance
        instance = await self.discovery.discover(service_name)

        # Build full URL
        url = f"{instance.scheme}://{instance.host}:{instance.port}{path}"

        logger.info(f"Calling {method} {url} for service {service_name}")

        # Make HTTP request
        response = await self._http_client.request(method, url, **kwargs)
        response.raise_for_status()

        return response.json()

    async def close(self):
        """Close HTTP client."""
        await self._http_client.aclose()


async def get_service_client(discovery: ServiceDiscovery) -> ExternalServiceClient:
    """Factory function to create service client.

    Args:
        discovery: Service discovery from container

    Returns:
        Configured ExternalServiceClient
    """
    return ExternalServiceClient(discovery)
