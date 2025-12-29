"""Service discovery adapters."""

from bento.adapters.service_discovery.cached import CachedServiceDiscovery
from bento.adapters.service_discovery.config import (
    ServiceDiscoveryBackend,
    ServiceDiscoveryConfig,
)
from bento.adapters.service_discovery.env import EnvServiceDiscovery
from bento.adapters.service_discovery.kubernetes import KubernetesServiceDiscovery

__all__ = [
    "ServiceDiscoveryBackend",
    "ServiceDiscoveryConfig",
    "EnvServiceDiscovery",
    "KubernetesServiceDiscovery",
    "CachedServiceDiscovery",
]
