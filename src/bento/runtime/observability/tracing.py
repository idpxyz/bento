"""OpenTelemetry tracing integration."""

from typing import Any


class TracingManager:
    """Manages OpenTelemetry tracing configuration."""

    def __init__(self) -> None:
        """Initialize tracing manager."""
        self._tracer_provider: Any = None
        self._tracer: Any = None

    def enable_jaeger(
        self,
        service_name: str,
        host: str = "localhost",
        port: int = 6831,
    ) -> None:
        """Enable Jaeger tracing.

        Args:
            service_name: Service name for traces
            host: Jaeger agent host
            port: Jaeger agent port
        """
        try:
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            from opentelemetry.exporter.jaeger.thrift import JaegerExporter

            jaeger_exporter = JaegerExporter(
                agent_host_name=host,
                agent_port=port,
            )
            tracer_provider = TracerProvider()
            tracer_provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
            trace.set_tracer_provider(tracer_provider)

            self._tracer_provider = tracer_provider
            self._tracer = trace.get_tracer(__name__)
        except ImportError:
            raise ImportError(
                "OpenTelemetry not installed. "
                "Install with: pip install opentelemetry-api opentelemetry-sdk "
                "opentelemetry-exporter-jaeger"
            )

    def enable_otlp(self, endpoint: str = "http://localhost:4317") -> None:
        """Enable OTLP tracing.

        Args:
            endpoint: OTLP collector endpoint
        """
        try:
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )

            otlp_exporter = OTLPSpanExporter(endpoint=endpoint)
            tracer_provider = TracerProvider()
            tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
            trace.set_tracer_provider(tracer_provider)

            self._tracer_provider = tracer_provider
            self._tracer = trace.get_tracer(__name__)
        except ImportError:
            raise ImportError(
                "OpenTelemetry not installed. "
                "Install with: pip install opentelemetry-api opentelemetry-sdk "
                "opentelemetry-exporter-otlp"
            )

    def get_tracer(self) -> Any:
        """Get the tracer instance.

        Returns:
            Tracer instance or None if not configured
        """
        return self._tracer
