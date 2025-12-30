"""Observability Port - Application layer contract for observability.

This module defines the ObservabilityProvider protocol for tracing, metrics,
and logging across the application.

Observability enables:
1. Distributed tracing for request flow tracking
2. Metrics collection for performance monitoring
3. Structured logging for debugging and auditing
"""

from __future__ import annotations

from typing import Any, Protocol


class Span(Protocol):
    """Span protocol for distributed tracing.

    Represents a single unit of work in a distributed trace.
    """

    def set_attribute(self, key: str, value: Any) -> None:
        """Set an attribute on the span.

        Args:
            key: Attribute key
            value: Attribute value
        """
        ...

    def set_status(self, status: str, description: str = "") -> None:
        """Set the span status.

        Args:
            status: Status (ok, error)
            description: Optional status description
        """
        ...

    def record_exception(self, exception: Exception) -> None:
        """Record an exception on the span.

        Args:
            exception: Exception to record
        """
        ...

    def end(self) -> None:
        """End the span."""
        ...


class Tracer(Protocol):
    """Tracer protocol for distributed tracing.

    Example:
        ```python
        tracer = observability.get_tracer("order-service")

        async with tracer.start_span("create_order") as span:
            span.set_attribute("order_id", order_id)
            # ... do work ...
            span.set_status("ok")
        ```
    """

    def start_span(
        self,
        name: str,
        attributes: dict[str, Any] | None = None,
    ) -> Any:
        """Start a new span as context manager.

        Args:
            name: Span name
            attributes: Optional span attributes

        Returns:
            Context manager that yields Span instance

        Note:
            Use as: async with tracer.start_span("name") as span:
        """
        ...


class Counter(Protocol):
    """Counter metric (monotonically increasing)."""

    def add(self, value: float, attributes: dict[str, Any] | None = None) -> None:
        """Add to the counter.

        Args:
            value: Value to add
            attributes: Optional metric attributes
        """
        ...


class Gauge(Protocol):
    """Gauge metric (can increase or decrease)."""

    def set(self, value: float, attributes: dict[str, Any] | None = None) -> None:
        """Set the gauge value.

        Args:
            value: Value to set
            attributes: Optional metric attributes
        """
        ...


class Histogram(Protocol):
    """Histogram metric (distribution)."""

    def record(self, value: float, attributes: dict[str, Any] | None = None) -> None:
        """Record a value in the histogram.

        Args:
            value: Value to record
            attributes: Optional metric attributes
        """
        ...


class Meter(Protocol):
    """Meter protocol for metrics collection.

    Example:
        ```python
        meter = observability.get_meter("order-service")

        counter = meter.create_counter("orders_created")
        counter.add(1, {"status": "success"})

        histogram = meter.create_histogram("order_processing_time_ms")
        histogram.record(125.5, {"method": "create"})
        ```
    """

    def create_counter(self, name: str, description: str = "") -> Counter:
        """Create a counter metric.

        Args:
            name: Metric name
            description: Optional metric description

        Returns:
            Counter instance
        """
        ...

    def create_gauge(self, name: str, description: str = "") -> Gauge:
        """Create a gauge metric.

        Args:
            name: Metric name
            description: Optional metric description

        Returns:
            Gauge instance
        """
        ...

    def create_histogram(self, name: str, description: str = "") -> Histogram:
        """Create a histogram metric.

        Args:
            name: Metric name
            description: Optional metric description

        Returns:
            Histogram instance
        """
        ...


class Logger(Protocol):
    """Logger protocol for structured logging.

    Example:
        ```python
        logger = observability.get_logger("order-service")

        logger.info(
            "Order created",
            order_id="123",
            customer_id="456",
            total=99.99,
        )
        ```
    """

    def debug(self, message: str, **context: Any) -> None:
        """Log debug message with context."""
        ...

    def info(self, message: str, **context: Any) -> None:
        """Log info message with context."""
        ...

    def warning(self, message: str, **context: Any) -> None:
        """Log warning message with context."""
        ...

    def error(self, message: str, **context: Any) -> None:
        """Log error message with context."""
        ...

    def critical(self, message: str, **context: Any) -> None:
        """Log critical message with context."""
        ...


class ObservabilityProvider(Protocol):
    """ObservabilityProvider protocol - defines the contract for observability operations.

    This protocol abstracts observability mechanisms, allowing the application
    layer to use tracing, metrics, and logging without depending on specific
    implementations (OpenTelemetry, Prometheus, Jaeger, etc.).

    This is a Protocol (not ABC), enabling structural subtyping.

    Example:
        ```python
        # In application service
        class OrderService:
            def __init__(self, observability: ObservabilityProvider):
                self.tracer = observability.get_tracer("order-service")
                self.meter = observability.get_meter("order-service")
                self.logger = observability.get_logger("order-service")

            async def create_order(self, command: CreateOrderCommand):
                async with self.tracer.start_span("create_order") as span:
                    self.logger.info("Creating order", order_id=command.order_id)

                    # ... business logic ...

                    counter = self.meter.create_counter("orders_created")
                    counter.add(1, {"status": "success"})

        # Infrastructure provides implementation
        class OpenTelemetryProvider:
            def get_tracer(self, name: str) -> Tracer:
                # OpenTelemetry-specific implementation
                ...
        ```
    """

    def get_tracer(self, name: str) -> Tracer:
        """Get a tracer instance for distributed tracing.

        Args:
            name: Tracer name (usually module or service name)

        Returns:
            Tracer instance

        Example:
            ```python
            tracer = observability.get_tracer("order-service")
            async with tracer.start_span("process_order") as span:
                span.set_attribute("order_id", "123")
            ```
        """
        ...

    def get_meter(self, name: str) -> Meter:
        """Get a meter instance for metrics collection.

        Args:
            name: Meter name (usually module or service name)

        Returns:
            Meter instance

        Example:
            ```python
            meter = observability.get_meter("order-service")
            counter = meter.create_counter("requests_total")
            counter.add(1, {"method": "POST", "status": "200"})
            ```
        """
        ...

    def get_logger(self, name: str) -> Logger:
        """Get a logger instance for structured logging.

        Args:
            name: Logger name (usually module or service name)

        Returns:
            Logger instance

        Example:
            ```python
            logger = observability.get_logger("order-service")
            logger.info("Order created", order_id="123", total=99.99)
            ```
        """
        ...

    async def start(self) -> None:
        """Start the observability provider.

        This method should:
        1. Initialize tracing, metrics, and logging backends
        2. Set up exporters and processors
        3. Begin collecting observability data

        Usually called during application startup.
        """
        ...

    async def stop(self) -> None:
        """Stop the observability provider.

        This method should:
        1. Flush pending traces and metrics
        2. Stop exporters and processors
        3. Clean up resources

        Usually called during application shutdown.
        """
        ...
