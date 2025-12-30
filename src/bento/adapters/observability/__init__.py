"""Observability adapters for Bento Framework.

This module provides concrete implementations of the ObservabilityProvider protocol.

Available adapters:
- NoOpObservabilityProvider: No-operation provider (disabled observability)
- OpenTelemetryProvider: OpenTelemetry-based provider (production-ready)
"""

from bento.adapters.observability.noop import NoOpObservabilityProvider
from bento.adapters.observability.otel import OpenTelemetryProvider

__all__ = [
    "NoOpObservabilityProvider",
    "OpenTelemetryProvider",
]
