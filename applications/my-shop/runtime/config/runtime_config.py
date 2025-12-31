"""Runtime Configuration - BentoRuntime module setup.

Responsible for configuring and building the BentoRuntime instance with all required modules.
"""

from __future__ import annotations

import logging

from bento.core import set_global_message_renderer
from bento.runtime import BentoRuntime
from bento.runtime.builder.runtime_builder import RuntimeBuilder
from bento.runtime.modules.observability import ObservabilityModule

from config import settings
from runtime.modules.catalog import CatalogModule
from runtime.modules.identity import IdentityModule
from runtime.modules.infra import InfraModule
from runtime.modules.ordering import OrderingModule
from runtime.modules.service_discovery import create_service_discovery_module
from shared.i18n import CATALOG, MessageRenderer

logger = logging.getLogger(__name__)


def build_runtime() -> BentoRuntime:
    """Build runtime configuration with all modules.

    Returns:
        Configured but not yet initialized BentoRuntime
    """
    # Register i18n message renderer (Optional)
    renderer = MessageRenderer(CATALOG, default_locale="zh-CN")
    set_global_message_renderer(renderer)
    logger.info("✅ i18n message renderer registered (default locale: zh-CN)")

    # Build module list
    modules = [
        InfraModule(),
        CatalogModule(),
        IdentityModule(),
        OrderingModule(),
        create_service_discovery_module(),
    ]

    # Add observability module based on configuration
    if settings.observability_enabled and settings.observability_provider == "otel":
        # Production: OpenTelemetry
        logger.info(f"Enabling OpenTelemetry observability (service: {settings.otel_service_name})")
        modules.append(
            ObservabilityModule(
                provider_type="otel",
                service_name=settings.otel_service_name,
                trace_exporter=settings.otel_trace_exporter,
                jaeger_host=settings.otel_jaeger_host,
                jaeger_port=settings.otel_jaeger_port,
                metrics_exporter=settings.otel_metrics_exporter,
                prometheus_port=settings.otel_prometheus_port,
            )
        )
    else:
        # Development: NoOp (zero overhead)
        logger.info("Using NoOp observability provider (zero overhead)")
        modules.append(ObservabilityModule(provider_type="noop"))

    return (
        RuntimeBuilder()
        .with_config(
            service_name="my-shop",
            environment=settings.app_env,
        )
        .with_database(url=settings.database_url)
        .with_modules(*modules)
        .build_runtime()
    )


# Global runtime instance for DI exports
_runtime: BentoRuntime | None = None


def get_runtime() -> BentoRuntime:
    """Get or create the global runtime instance.

    Note: Returns runtime without async initialization for DI purposes.
    Actual initialization happens in FastAPI lifespan.

    Returns:
        BentoRuntime instance (may not be fully initialized yet)
    """
    global _runtime
    if _runtime is None:
        _runtime = build_runtime()
        logger.info("BentoRuntime instance created (will be initialized in lifespan)")
    return _runtime
