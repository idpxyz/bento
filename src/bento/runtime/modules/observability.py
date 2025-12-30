"""Observability Module for Bento Runtime.

This module provides observability integration for the Bento Runtime,
supporting distributed tracing, metrics, and logging.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from bento.runtime.module import BentoModule

if TYPE_CHECKING:
    from bento.runtime.container import BentoContainer

logger = logging.getLogger(__name__)


class ObservabilityModule(BentoModule):
    """Bento Module for Observability Integration.

    Provides distributed tracing, metrics, and logging capabilities
    using pluggable observability providers.

    Example:
        ```python
        from bento.runtime import RuntimeBuilder
        from bento.runtime.modules.observability import ObservabilityModule

        # Development (no-op)
        runtime = (
            RuntimeBuilder()
            .with_modules(
                ObservabilityModule(provider_type="noop"),
                OrderingModule(),
            )
            .build_runtime()
        )

        # Production (OpenTelemetry)
        runtime = (
            RuntimeBuilder()
            .with_modules(
                ObservabilityModule(
                    provider_type="otel",
                    service_name="my-shop",
                    trace_exporter="jaeger",
                    jaeger_host="localhost",
                    jaeger_port=6831,
                    metrics_exporter="prometheus",
                ),
                OrderingModule(),
            )
            .build_runtime()
        )
        ```
    """

    name = "observability"

    def __init__(
        self,
        provider_type: str = "noop",
        service_name: str | None = None,
        **config: Any,
    ) -> None:
        """Initialize observability module.

        Args:
            provider_type: Provider type (noop, otel)
            service_name: Service name for observability
            **config: Provider-specific configuration
        """
        super().__init__()
        self.provider_type = provider_type
        self.service_name = service_name
        self.config = config
        self._provider: Any = None

    async def on_register(self, container: BentoContainer) -> None:
        """Register observability provider in container."""
        service_name = self.service_name or "bento-service"

        logger.info(
            f"Registering observability module: "
            f"provider={self.provider_type}, service={service_name}"
        )

        # Create provider based on type
        if self.provider_type == "otel":
            from bento.adapters.observability.otel import OpenTelemetryProvider

            self._provider = OpenTelemetryProvider(
                service_name=service_name,
                **self.config,
            )
        else:
            from bento.adapters.observability.noop import NoOpObservabilityProvider

            self._provider = NoOpObservabilityProvider()

        # Start provider
        await self._provider.start()

        # Register in container
        container.set("observability", self._provider)

        logger.info(f"Observability provider registered: {self.provider_type}")

    async def on_shutdown(self, container: BentoContainer) -> None:
        """Shutdown observability provider."""
        if self._provider:
            logger.info("Shutting down observability provider")
            await self._provider.stop()
            logger.info("Observability provider stopped")
