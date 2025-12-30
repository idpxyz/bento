"""Cached service discovery decorator."""

from __future__ import annotations

import logging
import time

from bento.application.ports.service_discovery import (
    ServiceDiscovery,
    ServiceInstance,
)

logger = logging.getLogger(__name__)


class CachedServiceDiscovery(ServiceDiscovery):
    """Decorator that adds caching to service discovery.

    Caches discovered service instances to reduce calls to underlying discovery.

    Example:
        ```python
        discovery = EnvServiceDiscovery()
        cached_discovery = CachedServiceDiscovery(discovery, ttl=300)
        instance = await cached_discovery.discover("catalog-service")
        ```
    """

    def __init__(self, discovery: ServiceDiscovery, ttl: int = 300):
        """Initialize cached service discovery.

        Args:
            discovery: Underlying service discovery implementation
            ttl: Time to live for cache entries in seconds
        """
        self.discovery = discovery
        self.ttl = ttl
        self.cache: dict[str, tuple[list[ServiceInstance], float]] = {}

    async def discover(
        self, service_name: str, strategy: str = "round_robin"
    ) -> ServiceInstance:
        """Discover with caching."""
        instances = await self.discover_all(service_name)

        if not instances:
            from bento.application.ports.service_discovery import ServiceNotFoundError

            raise ServiceNotFoundError(f"Service {service_name} not found")

        if strategy == "round_robin":
            return instances[0]
        elif strategy == "random":
            import random

            return random.choice(instances)
        else:
            return instances[0]

    async def discover_all(self, service_name: str) -> list[ServiceInstance]:
        """Discover all with caching."""
        now = time.time()

        # Check cache
        if service_name in self.cache:
            instances, timestamp = self.cache[service_name]
            if now - timestamp < self.ttl:
                logger.debug(f"Cache hit for {service_name}")
                return instances

        # Query underlying discovery
        logger.debug(f"Cache miss for {service_name}, querying underlying discovery")
        instances = await self.discovery.discover_all(service_name)

        # Cache result
        self.cache[service_name] = (instances, now)

        return instances

    async def register(
        self,
        service_name: str,
        host: str,
        port: int,
        metadata: dict | None = None,
    ) -> None:
        """Register and invalidate cache."""
        await self.discovery.register(service_name, host, port, metadata)
        self.cache.pop(service_name, None)
        logger.debug(f"Invalidated cache for {service_name}")

    async def deregister(
        self, service_name: str, host: str, port: int
    ) -> None:
        """Deregister and invalidate cache."""
        await self.discovery.deregister(service_name, host, port)
        self.cache.pop(service_name, None)
        logger.debug(f"Invalidated cache for {service_name}")

    async def health_check(
        self, service_name: str, host: str, port: int
    ) -> bool:
        """Health check."""
        return await self.discovery.health_check(service_name, host, port)

    def clear_cache(self) -> None:
        """Clear all cached entries."""
        self.cache.clear()
        logger.debug("Cleared service discovery cache")

    def clear_cache_for(self, service_name: str) -> None:
        """Clear cache for a specific service."""
        self.cache.pop(service_name, None)
        logger.debug(f"Cleared cache for {service_name}")
