"""Consul based service discovery."""

from __future__ import annotations

import logging

from bento.application.ports.service_discovery import (
    ServiceDiscovery,
    ServiceInstance,
    ServiceNotFoundError,
)

logger = logging.getLogger(__name__)


class ConsulServiceDiscovery(ServiceDiscovery):
    """Service discovery using Consul.

    Example:
        ```python
        discovery = ConsulServiceDiscovery(consul_url="http://localhost:8500")
        instance = await discovery.discover("catalog-service")
        ```
    """

    def __init__(self, consul_url: str = "http://localhost:8500"):
        """Initialize Consul service discovery.

        Args:
            consul_url: URL of Consul server
        """
        self.consul_url = consul_url

    async def discover(self, service_name: str, strategy: str = "round_robin") -> ServiceInstance:
        """Discover service from Consul."""
        instances = await self.discover_all(service_name)

        if not instances:
            raise ServiceNotFoundError(f"Service {service_name} not found in Consul")

        # Apply load balancing strategy
        if strategy == "round_robin":
            return instances[0]
        elif strategy == "random":
            import random

            return random.choice(instances)
        else:
            return instances[0]

    async def discover_all(self, service_name: str) -> list[ServiceInstance]:
        """Discover all instances from Consul."""
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                url = f"{self.consul_url}/v1/catalog/service/{service_name}"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status != 200:
                        logger.warning(
                            f"Failed to discover {service_name} from Consul: {resp.status}"
                        )
                        return []

                    services = await resp.json()

                    return [
                        ServiceInstance(
                            service_name=service_name,
                            host=svc["ServiceAddress"],
                            port=svc["ServicePort"],
                            metadata=svc.get("ServiceMeta", {}),
                        )
                        for svc in services
                    ]
        except Exception as e:
            logger.error(f"Error discovering {service_name} from Consul: {e}")
            return []

    async def register(
        self,
        service_name: str,
        host: str,
        port: int,
        metadata: dict | None = None,
    ) -> None:
        """Register service in Consul."""
        try:
            import aiohttp

            service_id = f"{service_name}-{host}-{port}"

            payload = {
                "ID": service_id,
                "Name": service_name,
                "Address": host,
                "Port": port,
                "Meta": metadata or {},
            }

            async with aiohttp.ClientSession() as session:
                url = f"{self.consul_url}/v1/agent/service/register"
                async with session.put(url, json=payload) as resp:
                    if resp.status not in (200, 201):
                        logger.error(f"Failed to register {service_name} in Consul: {resp.status}")
        except Exception as e:
            logger.error(f"Error registering {service_name} in Consul: {e}")

    async def deregister(self, service_name: str, host: str, port: int) -> None:
        """Deregister service from Consul."""
        try:
            import aiohttp

            service_id = f"{service_name}-{host}-{port}"

            async with aiohttp.ClientSession() as session:
                url = f"{self.consul_url}/v1/agent/service/deregister/{service_id}"
                async with session.put(url) as resp:
                    if resp.status not in (200, 201):
                        logger.error(
                            f"Failed to deregister {service_name} from Consul: {resp.status}"
                        )
        except Exception as e:
            logger.error(f"Error deregistering {service_name} from Consul: {e}")

    async def health_check(self, service_name: str, host: str, port: int) -> bool:
        """Check service health in Consul."""
        try:
            instances = await self.discover_all(service_name)
            for instance in instances:
                if instance.host == host and instance.port == port:
                    return True
            return False
        except Exception as e:
            logger.error(f"Error checking health of {service_name}: {e}")
            return False
