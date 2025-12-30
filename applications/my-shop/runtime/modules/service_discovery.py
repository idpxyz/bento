"""Service Discovery Module for my-shop application.

Integrates Bento Framework's service discovery capabilities into the my-shop runtime.
"""

from __future__ import annotations

import logging

from bento.adapters.service_discovery.config import (
    ServiceDiscoveryBackend,
    ServiceDiscoveryConfig,
)
from bento.runtime.integrations.service_discovery import (
    ServiceDiscoveryModule as BentoServiceDiscoveryModule,
)

from config import settings

logger = logging.getLogger(__name__)


def create_service_discovery_module() -> BentoServiceDiscoveryModule:
    """Create service discovery module from application settings.

    Returns:
        Configured ServiceDiscoveryModule instance
    """
    config = ServiceDiscoveryConfig(
        backend=ServiceDiscoveryBackend(settings.service_discovery_backend),
        timeout=settings.service_discovery_timeout,
        retry_count=settings.service_discovery_retry,
        cache_ttl=settings.service_discovery_cache_ttl,
        consul_url=settings.consul_url,
        consul_datacenter=settings.consul_datacenter,
        kubernetes_namespace=settings.kubernetes_namespace,
        kubernetes_service_suffix=settings.kubernetes_service_suffix,
    )

    logger.info(
        f"Creating service discovery module with backend: {config.backend}"
    )

    return BentoServiceDiscoveryModule(config)
