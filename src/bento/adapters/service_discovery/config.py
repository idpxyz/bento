"""Service discovery configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum


class ServiceDiscoveryBackend(str, Enum):
    """Supported service discovery backends."""

    ENV = "env"
    CONSUL = "consul"
    EUREKA = "eureka"
    KUBERNETES = "kubernetes"
    STATIC = "static"


@dataclass
class ServiceDiscoveryConfig:
    """Configuration for service discovery."""

    backend: ServiceDiscoveryBackend

    # Common settings
    timeout: int = 5
    retry_count: int = 3
    cache_ttl: int = 300

    # Consul settings
    consul_url: str | None = None
    consul_datacenter: str = "dc1"

    # Eureka settings
    eureka_url: str | None = None
    eureka_app_name: str | None = None

    # Kubernetes settings
    kubernetes_namespace: str = "default"
    kubernetes_service_suffix: str = "svc.cluster.local"

    # Static settings (for development)
    static_services: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> ServiceDiscoveryConfig:
        """Create config from environment variables."""
        backend_str = os.getenv("SERVICE_DISCOVERY_BACKEND", "env")

        return cls(
            backend=ServiceDiscoveryBackend(backend_str),
            timeout=int(os.getenv("SERVICE_DISCOVERY_TIMEOUT", "5")),
            retry_count=int(os.getenv("SERVICE_DISCOVERY_RETRY", "3")),
            cache_ttl=int(os.getenv("SERVICE_DISCOVERY_CACHE_TTL", "300")),
            consul_url=os.getenv("CONSUL_URL"),
            eureka_url=os.getenv("EUREKA_URL"),
            kubernetes_namespace=os.getenv("KUBERNETES_NAMESPACE", "default"),
        )
