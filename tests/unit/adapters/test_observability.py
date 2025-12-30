"""Complete test suite for observability adapters."""

from __future__ import annotations

import pytest

from bento.adapters.observability.noop import (
    NoOpCounter,
    NoOpGauge,
    NoOpHistogram,
    NoOpLogger,
    NoOpMeter,
    NoOpObservabilityProvider,
    NoOpSpan,
    NoOpTracer,
)
from bento.adapters.observability.otel import OpenTelemetryProvider


class TestNoOpSpan:
    """Test NoOp span implementation."""

    def test_set_attribute(self):
        """Test setting attributes (no-op)."""
        span = NoOpSpan()
        span.set_attribute("key", "value")
        span.set_attribute("number", 123)
        # Should not raise any errors

    def test_set_status(self):
        """Test setting status (no-op)."""
        span = NoOpSpan()
        span.set_status("ok")
        span.set_status("error", "Something went wrong")
        # Should not raise any errors

    def test_record_exception(self):
        """Test recording exception (no-op)."""
        span = NoOpSpan()
        span.record_exception(ValueError("test error"))
        # Should not raise any errors

    def test_end(self):
        """Test ending span (no-op)."""
        span = NoOpSpan()
        span.end()
        # Should not raise any errors


class TestNoOpTracer:
    """Test NoOp tracer implementation."""

    @pytest.mark.asyncio
    async def test_start_span(self):
        """Test starting a span."""
        tracer = NoOpTracer()

        async with tracer.start_span("test-operation") as span:
            assert isinstance(span, NoOpSpan)
            span.set_attribute("test", "value")

    @pytest.mark.asyncio
    async def test_start_span_with_attributes(self):
        """Test starting a span with attributes."""
        tracer = NoOpTracer()

        async with tracer.start_span(
            "test-operation",
            {"key1": "value1", "key2": 123},
        ) as span:
            assert isinstance(span, NoOpSpan)


class TestNoOpMetrics:
    """Test NoOp metrics implementations."""

    def test_counter(self):
        """Test counter operations."""
        counter = NoOpCounter()
        counter.add(1)
        counter.add(5, {"status": "success"})
        # Should not raise any errors

    def test_gauge(self):
        """Test gauge operations."""
        gauge = NoOpGauge()
        gauge.set(100)
        gauge.set(50.5, {"region": "us-west"})
        # Should not raise any errors

    def test_histogram(self):
        """Test histogram operations."""
        histogram = NoOpHistogram()
        histogram.record(125.5)
        histogram.record(200, {"method": "POST"})
        # Should not raise any errors


class TestNoOpMeter:
    """Test NoOp meter implementation."""

    def test_create_counter(self):
        """Test creating a counter."""
        meter = NoOpMeter()
        counter = meter.create_counter("test_counter")
        assert isinstance(counter, NoOpCounter)

    def test_create_counter_with_description(self):
        """Test creating a counter with description."""
        meter = NoOpMeter()
        counter = meter.create_counter("test_counter", "Test counter description")
        assert isinstance(counter, NoOpCounter)

    def test_create_gauge(self):
        """Test creating a gauge."""
        meter = NoOpMeter()
        gauge = meter.create_gauge("test_gauge")
        assert isinstance(gauge, NoOpGauge)

    def test_create_histogram(self):
        """Test creating a histogram."""
        meter = NoOpMeter()
        histogram = meter.create_histogram("test_histogram")
        assert isinstance(histogram, NoOpHistogram)


class TestNoOpLogger:
    """Test NoOp logger implementation."""

    def test_debug(self):
        """Test debug logging."""
        logger = NoOpLogger()
        logger.debug("Debug message", key="value")
        # Should not raise any errors

    def test_info(self):
        """Test info logging."""
        logger = NoOpLogger()
        logger.info("Info message", user_id="123")
        # Should not raise any errors

    def test_warning(self):
        """Test warning logging."""
        logger = NoOpLogger()
        logger.warning("Warning message", code=404)
        # Should not raise any errors

    def test_error(self):
        """Test error logging."""
        logger = NoOpLogger()
        logger.error("Error message", error="Something went wrong")
        # Should not raise any errors

    def test_critical(self):
        """Test critical logging."""
        logger = NoOpLogger()
        logger.critical("Critical message", severity="high")
        # Should not raise any errors


class TestNoOpObservabilityProvider:
    """Test NoOp observability provider."""

    def test_initialization(self):
        """Test provider initialization."""
        provider = NoOpObservabilityProvider()
        assert provider is not None

    def test_get_tracer(self):
        """Test getting a tracer."""
        provider = NoOpObservabilityProvider()
        tracer = provider.get_tracer("test-service")
        assert isinstance(tracer, NoOpTracer)

    def test_get_tracer_multiple_calls(self):
        """Test getting tracer returns same instance."""
        provider = NoOpObservabilityProvider()
        tracer1 = provider.get_tracer("test-service")
        tracer2 = provider.get_tracer("test-service")
        assert tracer1 is tracer2

    def test_get_meter(self):
        """Test getting a meter."""
        provider = NoOpObservabilityProvider()
        meter = provider.get_meter("test-service")
        assert isinstance(meter, NoOpMeter)

    def test_get_meter_multiple_calls(self):
        """Test getting meter returns same instance."""
        provider = NoOpObservabilityProvider()
        meter1 = provider.get_meter("test-service")
        meter2 = provider.get_meter("test-service")
        assert meter1 is meter2

    def test_get_logger(self):
        """Test getting a logger."""
        provider = NoOpObservabilityProvider()
        logger = provider.get_logger("test-service")
        assert isinstance(logger, NoOpLogger)

    def test_get_logger_multiple_calls(self):
        """Test getting logger returns same instance."""
        provider = NoOpObservabilityProvider()
        logger1 = provider.get_logger("test-service")
        logger2 = provider.get_logger("test-service")
        assert logger1 is logger2

    @pytest.mark.asyncio
    async def test_start(self):
        """Test starting the provider."""
        provider = NoOpObservabilityProvider()
        await provider.start()
        # Should not raise any errors

    @pytest.mark.asyncio
    async def test_stop(self):
        """Test stopping the provider."""
        provider = NoOpObservabilityProvider()
        await provider.stop()
        # Should not raise any errors

    @pytest.mark.asyncio
    async def test_full_lifecycle(self):
        """Test complete provider lifecycle."""
        provider = NoOpObservabilityProvider()

        await provider.start()

        # Use tracer
        tracer = provider.get_tracer("test-service")
        async with tracer.start_span("test-operation") as span:
            span.set_attribute("test", "value")

        # Use meter
        meter = provider.get_meter("test-service")
        counter = meter.create_counter("test_counter")
        counter.add(1)

        # Use logger
        logger = provider.get_logger("test-service")
        logger.info("Test message")

        await provider.stop()


class TestOpenTelemetryProvider:
    """Test OpenTelemetry provider."""

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test provider initialization."""
        provider = OpenTelemetryProvider(
            service_name="test-service",
            trace_exporter="console",
        )
        assert provider.service_name == "test-service"
        assert provider.trace_exporter == "console"

    @pytest.mark.asyncio
    async def test_start_without_opentelemetry(self):
        """Test starting provider without OpenTelemetry installed."""
        provider = OpenTelemetryProvider(
            service_name="test-service",
            trace_exporter="console",
        )

        # Should not raise error even without OpenTelemetry
        await provider.start()

    @pytest.mark.asyncio
    async def test_stop(self):
        """Test stopping provider."""
        provider = OpenTelemetryProvider(
            service_name="test-service",
        )

        await provider.start()
        await provider.stop()

    @pytest.mark.asyncio
    async def test_get_tracer(self):
        """Test getting a tracer."""
        provider = OpenTelemetryProvider(
            service_name="test-service",
        )

        await provider.start()
        tracer = provider.get_tracer("test-service")
        assert tracer is not None

    @pytest.mark.asyncio
    async def test_get_meter(self):
        """Test getting a meter."""
        provider = OpenTelemetryProvider(
            service_name="test-service",
        )

        await provider.start()
        meter = provider.get_meter("test-service")
        assert meter is not None

    @pytest.mark.asyncio
    async def test_get_logger(self):
        """Test getting a logger."""
        provider = OpenTelemetryProvider(
            service_name="test-service",
        )

        await provider.start()
        logger = provider.get_logger("test-service")
        assert logger is not None

    @pytest.mark.asyncio
    async def test_jaeger_configuration(self):
        """Test Jaeger exporter configuration."""
        provider = OpenTelemetryProvider(
            service_name="test-service",
            trace_exporter="jaeger",
            jaeger_host="localhost",
            jaeger_port=6831,
        )

        await provider.start()
        assert provider.trace_exporter == "jaeger"

    @pytest.mark.asyncio
    async def test_otlp_configuration(self):
        """Test OTLP exporter configuration."""
        provider = OpenTelemetryProvider(
            service_name="test-service",
            trace_exporter="otlp",
            otlp_endpoint="http://localhost:4317",
        )

        await provider.start()
        assert provider.trace_exporter == "otlp"

    @pytest.mark.asyncio
    async def test_prometheus_configuration(self):
        """Test Prometheus exporter configuration."""
        provider = OpenTelemetryProvider(
            service_name="test-service",
            metrics_exporter="prometheus",
            prometheus_prefix="myapp_",
        )

        await provider.start()
        assert provider.metrics_exporter == "prometheus"

    @pytest.mark.asyncio
    async def test_full_lifecycle_without_otel(self):
        """Test complete lifecycle without OpenTelemetry installed."""
        provider = OpenTelemetryProvider(
            service_name="test-service",
            trace_exporter="console",
            metrics_exporter="console",
        )

        await provider.start()

        # Should return fallback implementations
        tracer = provider.get_tracer("test-service")
        meter = provider.get_meter("test-service")
        logger = provider.get_logger("test-service")

        assert tracer is not None
        assert meter is not None
        assert logger is not None

        # Should be able to use them without errors
        async with tracer.start_span("test-operation") as span:
            span.set_attribute("test", "value")

        counter = meter.create_counter("test_counter")
        counter.add(1)

        logger.info("Test message", key="value")

        await provider.stop()


class TestObservabilityIntegration:
    """Integration tests for observability."""

    @pytest.mark.asyncio
    async def test_noop_provider_complete_workflow(self):
        """Test complete workflow with NoOp provider."""
        provider = NoOpObservabilityProvider()
        await provider.start()

        # Get all components
        tracer = provider.get_tracer("order-service")
        meter = provider.get_meter("order-service")
        logger = provider.get_logger("order-service")

        # Simulate order creation workflow
        async with tracer.start_span("create_order") as span:
            span.set_attribute("order_id", "order-123")
            span.set_attribute("customer_id", "customer-456")

            logger.info(
                "Creating order",
                order_id="order-123",
                customer_id="customer-456",
            )

            # Record metrics
            counter = meter.create_counter("orders_created")
            counter.add(1, {"status": "initiated"})

            histogram = meter.create_histogram("order_value")
            histogram.record(99.99, {"currency": "USD"})

            # Simulate processing
            logger.debug("Processing order items")

            # Success
            span.set_status("ok")
            counter.add(1, {"status": "completed"})
            logger.info("Order created successfully")

        await provider.stop()

    @pytest.mark.asyncio
    async def test_otel_provider_complete_workflow(self):
        """Test complete workflow with OpenTelemetry provider."""
        provider = OpenTelemetryProvider(
            service_name="order-service",
            trace_exporter="console",
            metrics_exporter="console",
        )
        await provider.start()

        # Get all components
        tracer = provider.get_tracer("order-service")
        meter = provider.get_meter("order-service")
        logger = provider.get_logger("order-service")

        # Simulate order creation workflow
        async with tracer.start_span("create_order") as span:
            span.set_attribute("order_id", "order-123")

            logger.info("Creating order", order_id="order-123")

            counter = meter.create_counter("orders_created")
            counter.add(1)

            span.set_status("ok")

        await provider.stop()

    @pytest.mark.asyncio
    async def test_error_handling_workflow(self):
        """Test error handling in observability workflow."""
        provider = NoOpObservabilityProvider()
        await provider.start()

        tracer = provider.get_tracer("order-service")
        meter = provider.get_meter("order-service")
        logger = provider.get_logger("order-service")

        try:
            async with tracer.start_span("create_order") as span:
                span.set_attribute("order_id", "order-123")

                logger.info("Creating order")

                # Simulate error
                raise ValueError("Insufficient inventory")

        except ValueError as e:
            # Error handling
            logger.error("Order creation failed", error=str(e))

            counter = meter.create_counter("orders_failed")
            counter.add(1, {"error_type": "ValueError"})

        await provider.stop()
