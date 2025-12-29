"""OpenTelemetry configuration and initialization."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def setup_tracing(
    service_name: str,
    trace_exporter: str = "console",
    **exporter_kwargs: Any,
) -> None:
    """Setup OpenTelemetry tracing.

    Args:
        service_name: Service name for traces
        trace_exporter: Exporter type: "console", "jaeger", "otlp" (default: "console")
        **exporter_kwargs: Additional exporter configuration
    """
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        tracer_provider = TracerProvider()

        if trace_exporter == "console":
            from opentelemetry.sdk.trace.export import ConsoleSpanExporter
            from opentelemetry.sdk.trace.export import SimpleSpanProcessor

            processor = SimpleSpanProcessor(ConsoleSpanExporter())
            tracer_provider.add_span_processor(processor)

        elif trace_exporter == "jaeger":
            from opentelemetry.exporter.jaeger.thrift import JaegerExporter

            jaeger_exporter = JaegerExporter(
                agent_host_name=exporter_kwargs.get("jaeger_host", "localhost"),
                agent_port=exporter_kwargs.get("jaeger_port", 6831),
            )
            tracer_provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))

        elif trace_exporter == "otlp":
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )

            otlp_exporter = OTLPSpanExporter(
                endpoint=exporter_kwargs.get("otlp_endpoint", "http://localhost:4317"),
            )
            tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

        trace.set_tracer_provider(tracer_provider)

        logger.info(
            f"OpenTelemetry tracing enabled: "
            f"service={service_name}, exporter={trace_exporter}"
        )

        return tracer_provider

    except ImportError:
        logger.warning(
            "OpenTelemetry not installed. "
            "Install with: pip install opentelemetry-api opentelemetry-sdk"
        )
        return None


def setup_metrics(
    metrics_exporter: str = "console",
    **exporter_kwargs: Any,
) -> None:
    """Setup OpenTelemetry metrics.

    Args:
        metrics_exporter: Exporter type: "console", "prometheus", "otlp" (default: "console")
        **exporter_kwargs: Additional exporter configuration
    """
    try:
        from opentelemetry import metrics
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

        if metrics_exporter == "prometheus":
            from opentelemetry.exporter.prometheus import PrometheusMetricReader

            reader = PrometheusMetricReader(
                prefix=exporter_kwargs.get("prometheus_prefix", "bento_"),
            )
            meter_provider = MeterProvider(metric_readers=[reader])

        elif metrics_exporter == "otlp":
            from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
                OTLPMetricExporter,
            )

            otlp_exporter = OTLPMetricExporter(
                endpoint=exporter_kwargs.get("otlp_endpoint", "http://localhost:4317"),
            )
            reader = PeriodicExportingMetricReader(otlp_exporter)
            meter_provider = MeterProvider(metric_readers=[reader])

        else:  # console
            from opentelemetry.sdk.metrics.export import ConsoleMetricExporter

            reader = PeriodicExportingMetricReader(ConsoleMetricExporter())
            meter_provider = MeterProvider(metric_readers=[reader])

        metrics.set_meter_provider(meter_provider)

        logger.info(f"OpenTelemetry metrics enabled: exporter={metrics_exporter}")

        return meter_provider

    except ImportError:
        logger.warning(
            "OpenTelemetry not installed. "
            "Install with: pip install opentelemetry-api opentelemetry-sdk"
        )
        return None
