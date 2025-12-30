"""OpenTelemetry Observability Provider.

This adapter provides OpenTelemetry-based implementation of the ObservabilityProvider
protocol, supporting distributed tracing, metrics, and logging.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

logger = logging.getLogger(__name__)


class OpenTelemetrySpan:
    """OpenTelemetry span wrapper."""

    def __init__(self, span: Any) -> None:
        """Initialize span wrapper.

        Args:
            span: OpenTelemetry span instance
        """
        self._span = span

    def set_attribute(self, key: str, value: Any) -> None:
        """Set span attribute."""
        if self._span:
            self._span.set_attribute(key, value)

    def set_status(self, status: str, description: str = "") -> None:
        """Set span status."""
        if self._span:
            try:
                from opentelemetry.trace import Status, StatusCode

                status_code = StatusCode.OK if status == "ok" else StatusCode.ERROR
                self._span.set_status(Status(status_code, description))
            except ImportError:
                pass

    def record_exception(self, exception: Exception) -> None:
        """Record exception on span."""
        if self._span:
            self._span.record_exception(exception)

    def end(self) -> None:
        """End span."""
        if self._span:
            self._span.end()


class OpenTelemetryTracer:
    """OpenTelemetry tracer wrapper."""

    def __init__(self, tracer: Any) -> None:
        """Initialize tracer wrapper.

        Args:
            tracer: OpenTelemetry tracer instance
        """
        self._tracer = tracer

    @asynccontextmanager
    async def start_span(
        self,
        name: str,
        attributes: dict[str, Any] | None = None,
    ):
        """Start a new span."""
        if self._tracer:
            span = self._tracer.start_span(name)
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, value)

            wrapped_span = OpenTelemetrySpan(span)
            try:
                yield wrapped_span
            finally:
                wrapped_span.end()
        else:
            # Fallback to no-op
            from bento.adapters.observability.noop import NoOpSpan

            yield NoOpSpan()


class OpenTelemetryCounter:
    """OpenTelemetry counter wrapper."""

    def __init__(self, counter: Any) -> None:
        """Initialize counter wrapper."""
        self._counter = counter

    def add(self, value: float, attributes: dict[str, Any] | None = None) -> None:
        """Add to counter."""
        if self._counter:
            self._counter.add(value, attributes or {})


class OpenTelemetryGauge:
    """OpenTelemetry gauge wrapper."""

    def __init__(self, gauge: Any) -> None:
        """Initialize gauge wrapper."""
        self._gauge = gauge

    def set(self, value: float, attributes: dict[str, Any] | None = None) -> None:
        """Set gauge value."""
        if self._gauge:
            # OpenTelemetry doesn't have direct gauge support in all versions
            # This is a simplified implementation
            pass


class OpenTelemetryHistogram:
    """OpenTelemetry histogram wrapper."""

    def __init__(self, histogram: Any) -> None:
        """Initialize histogram wrapper."""
        self._histogram = histogram

    def record(self, value: float, attributes: dict[str, Any] | None = None) -> None:
        """Record value in histogram."""
        if self._histogram:
            self._histogram.record(value, attributes or {})


class OpenTelemetryMeter:
    """OpenTelemetry meter wrapper."""

    def __init__(self, meter: Any) -> None:
        """Initialize meter wrapper.

        Args:
            meter: OpenTelemetry meter instance
        """
        self._meter = meter
        self._counters: dict[str, Any] = {}
        self._histograms: dict[str, Any] = {}

    def create_counter(self, name: str, description: str = "") -> OpenTelemetryCounter:
        """Create counter metric."""
        if name not in self._counters and self._meter:
            self._counters[name] = self._meter.create_counter(
                name=name,
                description=description,
            )
        return OpenTelemetryCounter(self._counters.get(name))

    def create_gauge(self, name: str, description: str = "") -> OpenTelemetryGauge:
        """Create gauge metric."""
        # Simplified implementation
        return OpenTelemetryGauge(None)

    def create_histogram(self, name: str, description: str = "") -> OpenTelemetryHistogram:
        """Create histogram metric."""
        if name not in self._histograms and self._meter:
            self._histograms[name] = self._meter.create_histogram(
                name=name,
                description=description,
            )
        return OpenTelemetryHistogram(self._histograms.get(name))


class OpenTelemetryLogger:
    """OpenTelemetry logger wrapper (uses standard logging)."""

    def __init__(self, name: str) -> None:
        """Initialize logger wrapper.

        Args:
            name: Logger name
        """
        self._logger = logging.getLogger(name)

    def debug(self, message: str, **context: Any) -> None:
        """Log debug message."""
        self._logger.debug(message, extra=context)

    def info(self, message: str, **context: Any) -> None:
        """Log info message."""
        self._logger.info(message, extra=context)

    def warning(self, message: str, **context: Any) -> None:
        """Log warning message."""
        self._logger.warning(message, extra=context)

    def error(self, message: str, **context: Any) -> None:
        """Log error message."""
        self._logger.error(message, extra=context)

    def critical(self, message: str, **context: Any) -> None:
        """Log critical message."""
        self._logger.critical(message, extra=context)


class OpenTelemetryProvider:
    """OpenTelemetry observability provider.

    Provides tracing, metrics, and logging using OpenTelemetry SDK.

    Example:
        ```python
        provider = OpenTelemetryProvider(
            service_name="my-shop",
            trace_exporter="jaeger",
            jaeger_host="localhost",
            jaeger_port=6831,
        )
        await provider.start()

        tracer = provider.get_tracer("order-service")
        async with tracer.start_span("create_order") as span:
            span.set_attribute("order_id", "123")
        ```
    """

    def __init__(
        self,
        service_name: str,
        trace_exporter: str = "console",
        metrics_exporter: str = "console",
        **exporter_kwargs: Any,
    ) -> None:
        """Initialize OpenTelemetry provider.

        Args:
            service_name: Service name for observability
            trace_exporter: Trace exporter type (console, jaeger, otlp, or comma-separated list)
                          Examples: "console", "jaeger", "otlp", "console,jaeger", "console,otlp,jaeger"
            metrics_exporter: Metrics exporter type (console, prometheus, otlp, or comma-separated list)
                            Examples: "console", "prometheus", "otlp", "console,prometheus"
            **exporter_kwargs: Additional exporter configuration
        """
        self.service_name = service_name
        self.trace_exporter = trace_exporter
        self.metrics_exporter = metrics_exporter
        self.exporter_kwargs = exporter_kwargs

        self._tracer_provider: Any = None
        self._meter_provider: Any = None
        self._tracers: dict[str, OpenTelemetryTracer] = {}
        self._meters: dict[str, OpenTelemetryMeter] = {}
        self._loggers: dict[str, OpenTelemetryLogger] = {}

    async def start(self) -> None:
        """Start OpenTelemetry."""
        try:
            # Setup tracing
            self._tracer_provider = self._setup_tracing()

            # Setup metrics
            self._meter_provider = self._setup_metrics()

            logger.info(
                f"OpenTelemetry started: service={self.service_name}, "
                f"trace_exporter={self.trace_exporter}, "
                f"metrics_exporter={self.metrics_exporter}"
            )
        except ImportError as e:
            logger.warning(
                f"OpenTelemetry not fully installed: {e}. "
                "Install with: pip install opentelemetry-api opentelemetry-sdk"
            )

    async def stop(self) -> None:
        """Stop OpenTelemetry."""
        self._tracer_provider = None
        self._meter_provider = None
        self._tracers.clear()
        self._meters.clear()
        self._loggers.clear()
        logger.info("OpenTelemetry stopped")

    def _setup_tracing(self) -> Any:
        """Setup OpenTelemetry tracing with support for multiple exporters.

        Supports comma-separated exporters: "console,jaeger,otlp"
        """
        try:
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor

            tracer_provider = TracerProvider()

            # Parse exporters (support comma-separated list)
            exporters = [e.strip() for e in self.trace_exporter.split(",")]

            for exporter_type in exporters:
                if exporter_type == "console":
                    from opentelemetry.sdk.trace.export import (
                        ConsoleSpanExporter,
                        SimpleSpanProcessor,
                    )

                    processor = SimpleSpanProcessor(ConsoleSpanExporter())
                    tracer_provider.add_span_processor(processor)
                    logger.info("Added console trace exporter")

                elif exporter_type == "jaeger":
                    try:
                        from opentelemetry.exporter.jaeger.thrift import JaegerExporter

                        jaeger_host = self.exporter_kwargs.get("jaeger_host", "localhost")
                        jaeger_port = self.exporter_kwargs.get("jaeger_port", 6831)
                        jaeger_exporter = JaegerExporter(
                            agent_host_name=jaeger_host,
                            agent_port=jaeger_port,
                        )
                        tracer_provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
                        logger.info(f"Added Jaeger trace exporter: {jaeger_host}:{jaeger_port}")
                    except Exception as e:
                        logger.warning(
                            f"Failed to initialize Jaeger exporter ({self.exporter_kwargs.get('jaeger_host')}:{self.exporter_kwargs.get('jaeger_port')}): {e}. Traces will not be exported to Jaeger."
                        )

                elif exporter_type == "otlp":
                    try:
                        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                            OTLPSpanExporter,
                        )

                        otlp_endpoint = self.exporter_kwargs.get(
                            "otlp_endpoint", "http://localhost:4317"
                        )
                        otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
                        tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
                        logger.info(f"Added OTLP trace exporter: {otlp_endpoint}")
                    except Exception as e:
                        logger.warning(
                            f"Failed to initialize OTLP trace exporter ({self.exporter_kwargs.get('otlp_endpoint')}): {e}. Traces will not be exported to OTLP."
                        )

            trace.set_tracer_provider(tracer_provider)
            return tracer_provider

        except ImportError:
            logger.warning("OpenTelemetry tracing not available")
            return None

    def _setup_metrics(self) -> Any:
        """Setup OpenTelemetry metrics with support for multiple exporters.

        Supports comma-separated exporters: "console,prometheus,otlp"
        """
        try:
            from opentelemetry import metrics
            from opentelemetry.sdk.metrics import MeterProvider
            from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

            readers = []

            # Parse exporters (support comma-separated list)
            exporters = [e.strip() for e in self.metrics_exporter.split(",")]

            for exporter_type in exporters:
                if exporter_type == "console":
                    from opentelemetry.sdk.metrics.export import ConsoleMetricExporter

                    reader = PeriodicExportingMetricReader(ConsoleMetricExporter())
                    readers.append(reader)
                    logger.info("Added console metrics exporter")

                elif exporter_type == "prometheus":
                    try:
                        from opentelemetry.exporter.prometheus import PrometheusMetricReader

                        prometheus_host = self.exporter_kwargs.get("prometheus_host", "0.0.0.0")
                        prometheus_port = self.exporter_kwargs.get("prometheus_port", 9090)
                        prometheus_prefix = self.exporter_kwargs.get("prometheus_prefix", "bento_")

                        reader = PrometheusMetricReader(
                            prefix=prometheus_prefix,
                        )
                        readers.append(reader)
                        logger.info(
                            f"Added Prometheus metrics exporter (host: {prometheus_host}, port: {prometheus_port}, prefix: {prometheus_prefix})"
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to initialize Prometheus metrics exporter: {e}. Metrics will not be exported to Prometheus."
                        )

                elif exporter_type == "otlp":
                    try:
                        from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
                            OTLPMetricExporter,
                        )

                        otlp_endpoint = self.exporter_kwargs.get(
                            "otlp_endpoint", "http://localhost:4317"
                        )
                        otlp_exporter = OTLPMetricExporter(endpoint=otlp_endpoint)
                        reader = PeriodicExportingMetricReader(otlp_exporter)
                        readers.append(reader)
                        logger.info(f"Added OTLP metrics exporter: {otlp_endpoint}")
                    except Exception as e:
                        logger.warning(
                            f"Failed to initialize OTLP metrics exporter ({self.exporter_kwargs.get('otlp_endpoint')}): {e}. Metrics will not be exported to OTLP."
                        )

            meter_provider = MeterProvider(metric_readers=readers)
            metrics.set_meter_provider(meter_provider)
            return meter_provider

        except ImportError:
            logger.warning("OpenTelemetry metrics not available")
            return None

    def get_tracer(self, name: str) -> OpenTelemetryTracer:
        """Get a tracer instance."""
        if name not in self._tracers:
            if self._tracer_provider:
                from opentelemetry import trace

                tracer = trace.get_tracer(name)
                self._tracers[name] = OpenTelemetryTracer(tracer)
            else:
                # Fallback to no-op
                from bento.adapters.observability.noop import NoOpTracer

                self._tracers[name] = NoOpTracer()

        return self._tracers[name]

    def get_meter(self, name: str) -> OpenTelemetryMeter:
        """Get a meter instance."""
        if name not in self._meters:
            if self._meter_provider:
                from opentelemetry import metrics

                meter = metrics.get_meter(name)
                self._meters[name] = OpenTelemetryMeter(meter)
            else:
                # Fallback to no-op
                from bento.adapters.observability.noop import NoOpMeter

                self._meters[name] = NoOpMeter()

        return self._meters[name]

    def get_logger(self, name: str) -> OpenTelemetryLogger:
        """Get a logger instance."""
        if name not in self._loggers:
            self._loggers[name] = OpenTelemetryLogger(name)
        return self._loggers[name]
