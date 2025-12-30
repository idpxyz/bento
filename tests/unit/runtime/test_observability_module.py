"""Tests for observability runtime module."""

from __future__ import annotations

import pytest

from bento.adapters.observability.noop import NoOpObservabilityProvider
from bento.adapters.observability.otel import OpenTelemetryProvider
from bento.runtime.container import BentoContainer
from bento.runtime.modules.observability import ObservabilityModule


class TestObservabilityModule:
    """Test observability module."""

    def test_initialization_noop(self):
        """Test module initialization with NoOp provider."""
        module = ObservabilityModule(provider_type="noop")
        assert module.name == "observability"
        assert module.provider_type == "noop"

    def test_initialization_otel(self):
        """Test module initialization with OpenTelemetry provider."""
        module = ObservabilityModule(
            provider_type="otel",
            service_name="test-service",
            trace_exporter="console",
        )
        assert module.name == "observability"
        assert module.provider_type == "otel"
        assert module.service_name == "test-service"

    @pytest.mark.asyncio
    async def test_register_noop_provider(self):
        """Test registering NoOp provider."""
        module = ObservabilityModule(provider_type="noop")
        container = BentoContainer()

        await module.on_register(container)

        # Check provider is registered
        provider = container.get("observability")
        assert isinstance(provider, NoOpObservabilityProvider)

    @pytest.mark.asyncio
    async def test_register_otel_provider(self):
        """Test registering OpenTelemetry provider."""
        module = ObservabilityModule(
            provider_type="otel",
            service_name="test-service",
            trace_exporter="console",
        )
        container = BentoContainer()

        await module.on_register(container)

        # Check provider is registered
        provider = container.get("observability")
        assert isinstance(provider, OpenTelemetryProvider)
        assert provider.service_name == "test-service"

    @pytest.mark.asyncio
    async def test_shutdown(self):
        """Test module shutdown."""
        module = ObservabilityModule(provider_type="noop")
        container = BentoContainer()

        await module.on_register(container)
        await module.on_shutdown(container)

        # Provider should be stopped
        assert module._provider is not None

    @pytest.mark.asyncio
    async def test_default_service_name(self):
        """Test default service name."""
        module = ObservabilityModule(
            provider_type="otel",
            # No service_name provided
        )
        container = BentoContainer()

        await module.on_register(container)

        provider = container.get("observability")
        assert provider.service_name == "bento-service"

    @pytest.mark.asyncio
    async def test_custom_service_name(self):
        """Test custom service name."""
        module = ObservabilityModule(
            provider_type="otel",
            service_name="my-custom-service",
        )
        container = BentoContainer()

        await module.on_register(container)

        provider = container.get("observability")
        assert provider.service_name == "my-custom-service"

    @pytest.mark.asyncio
    async def test_otel_with_jaeger(self):
        """Test OpenTelemetry with Jaeger configuration."""
        module = ObservabilityModule(
            provider_type="otel",
            service_name="test-service",
            trace_exporter="jaeger",
            jaeger_host="localhost",
            jaeger_port=6831,
        )
        container = BentoContainer()

        await module.on_register(container)

        provider = container.get("observability")
        assert isinstance(provider, OpenTelemetryProvider)
        assert provider.trace_exporter == "jaeger"

    @pytest.mark.asyncio
    async def test_otel_with_prometheus(self):
        """Test OpenTelemetry with Prometheus configuration."""
        module = ObservabilityModule(
            provider_type="otel",
            service_name="test-service",
            metrics_exporter="prometheus",
            prometheus_prefix="myapp_",
        )
        container = BentoContainer()

        await module.on_register(container)

        provider = container.get("observability")
        assert isinstance(provider, OpenTelemetryProvider)
        assert provider.metrics_exporter == "prometheus"

    @pytest.mark.asyncio
    async def test_full_lifecycle(self):
        """Test complete module lifecycle."""
        module = ObservabilityModule(
            provider_type="otel",
            service_name="test-service",
            trace_exporter="console",
            metrics_exporter="console",
        )
        container = BentoContainer()

        # Register
        await module.on_register(container)

        # Use provider
        provider = container.get("observability")
        tracer = provider.get_tracer("test")
        meter = provider.get_meter("test")
        logger = provider.get_logger("test")

        assert tracer is not None
        assert meter is not None
        assert logger is not None

        # Shutdown
        await module.on_shutdown(container)
