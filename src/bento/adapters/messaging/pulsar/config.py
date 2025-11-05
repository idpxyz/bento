"""Pulsar Configuration - Settings for Pulsar client and message bus.

This module provides configuration for connecting to Apache Pulsar.
Supports:
- Service URL configuration
- Authentication (token-based)
- TLS/SSL settings
- Topic naming conventions
"""

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass
class PulsarConfig:
    """Pulsar client configuration.

    Provides settings for connecting to Apache Pulsar broker.

    Attributes:
        service_url: Pulsar broker URL (e.g., "pulsar://localhost:6650")
        auth_token: Authentication token (optional)
        tls_enabled: Enable TLS/SSL
        tls_trust_cert_path: Path to TLS certificate
        tls_validate_hostname: Validate TLS hostname
        tenant: Pulsar tenant (namespace prefix)
        namespace: Pulsar namespace
        topic_prefix: Prefix for topic names

    Example:
        ```python
        from bento.adapters.messaging.pulsar.config import PulsarConfig

        # From environment variables
        config = PulsarConfig.from_env()

        # Manual configuration
        config = PulsarConfig(
            service_url="pulsar://192.168.1.100:6650",
            tenant="public",
            namespace="default"
        )
        ```
    """

    service_url: str = "pulsar://localhost:6650"
    auth_token: str | None = None
    tls_enabled: bool = False
    tls_trust_cert_path: str | None = None
    tls_validate_hostname: bool = True
    tenant: str = "public"
    namespace: str = "default"
    topic_prefix: str = "persistent"

    @classmethod
    def from_env(cls) -> "PulsarConfig":
        """Create configuration from environment variables.

        Environment Variables:
            PULSAR_URL: Service URL (default: pulsar://localhost:6650)
            PULSAR_AUTH_TOKEN: Authentication token
            PULSAR_TLS_ENABLED: Enable TLS (true/false)
            PULSAR_TLS_CERT_PATH: TLS certificate path
            PULSAR_TLS_VALIDATE_HOSTNAME: Validate hostname (true/false)
            PULSAR_TENANT: Tenant name (default: public)
            PULSAR_NAMESPACE: Namespace name (default: default)
            PULSAR_TOPIC_PREFIX: Topic prefix (default: persistent)

        Returns:
            PulsarConfig instance
        """
        return cls(
            service_url=os.getenv("PULSAR_URL", "pulsar://localhost:6650"),
            auth_token=os.getenv("PULSAR_AUTH_TOKEN"),
            tls_enabled=os.getenv("PULSAR_TLS_ENABLED", "false").lower() == "true",
            tls_trust_cert_path=os.getenv("PULSAR_TLS_CERT_PATH"),
            tls_validate_hostname=os.getenv("PULSAR_TLS_VALIDATE_HOSTNAME", "true").lower()
            == "true",
            tenant=os.getenv("PULSAR_TENANT", "public"),
            namespace=os.getenv("PULSAR_NAMESPACE", "default"),
            topic_prefix=os.getenv("PULSAR_TOPIC_PREFIX", "persistent"),
        )

    def get_topic_fqn(self, topic_name: str) -> str:
        """Get fully qualified topic name.

        Args:
            topic_name: Simple topic name (e.g., "order.created")

        Returns:
            Fully qualified topic name (e.g., "persistent://public/default/order.created")

        Example:
            ```python
            config = PulsarConfig(tenant="acme", namespace="prod")
            fqn = config.get_topic_fqn("order.created")
            # Returns: "persistent://acme/prod/order.created"
            ```
        """
        return f"{self.topic_prefix}://{self.tenant}/{self.namespace}/{topic_name}"


@lru_cache(maxsize=1)
def get_pulsar_config() -> PulsarConfig:
    """Get global Pulsar configuration (singleton).

    Returns:
        PulsarConfig instance (cached)

    Example:
        ```python
        from bento.adapters.messaging.pulsar.config import get_pulsar_config

        config = get_pulsar_config()
        print(config.service_url)
        ```
    """
    return PulsarConfig.from_env()
