"""NoOp Observability Provider - No-operation implementation.

This adapter provides a no-operation implementation of the ObservabilityProvider
protocol. All methods are no-ops, making it suitable for:
- Development environments where observability is not needed
- Testing environments
- Disabling observability without code changes
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any


class NoOpSpan:
    """No-operation span implementation."""

    def set_attribute(self, key: str, value: Any) -> None:
        """Set attribute (no-op)."""
        pass

    def set_status(self, status: str, description: str = "") -> None:
        """Set status (no-op)."""
        pass

    def record_exception(self, exception: Exception) -> None:
        """Record exception (no-op)."""
        pass

    def end(self) -> None:
        """End span (no-op)."""
        pass


class NoOpTracer:
    """No-operation tracer implementation."""

    @asynccontextmanager
    async def start_span(
        self,
        name: str,
        attributes: dict[str, Any] | None = None,
    ):
        """Start span (no-op)."""
        yield NoOpSpan()


class NoOpCounter:
    """No-operation counter implementation."""

    def add(self, value: float, attributes: dict[str, Any] | None = None) -> None:
        """Add to counter (no-op)."""
        pass


class NoOpGauge:
    """No-operation gauge implementation."""

    def set(self, value: float, attributes: dict[str, Any] | None = None) -> None:
        """Set gauge (no-op)."""
        pass


class NoOpHistogram:
    """No-operation histogram implementation."""

    def record(self, value: float, attributes: dict[str, Any] | None = None) -> None:
        """Record value (no-op)."""
        pass


class NoOpMeter:
    """No-operation meter implementation."""

    def create_counter(self, name: str, description: str = "") -> NoOpCounter:
        """Create counter (no-op)."""
        return NoOpCounter()

    def create_gauge(self, name: str, description: str = "") -> NoOpGauge:
        """Create gauge (no-op)."""
        return NoOpGauge()

    def create_histogram(self, name: str, description: str = "") -> NoOpHistogram:
        """Create histogram (no-op)."""
        return NoOpHistogram()


class NoOpLogger:
    """No-operation logger implementation."""

    def debug(self, message: str, **context: Any) -> None:
        """Log debug (no-op)."""
        pass

    def info(self, message: str, **context: Any) -> None:
        """Log info (no-op)."""
        pass

    def warning(self, message: str, **context: Any) -> None:
        """Log warning (no-op)."""
        pass

    def error(self, message: str, **context: Any) -> None:
        """Log error (no-op)."""
        pass

    def critical(self, message: str, **context: Any) -> None:
        """Log critical (no-op)."""
        pass


class NoOpObservabilityProvider:
    """No-operation observability provider.

    Implements the ObservabilityProvider protocol with no-op methods.
    Useful for development, testing, or disabling observability.

    Example:
        ```python
        # Disable observability
        observability = NoOpObservabilityProvider()

        # All operations are no-ops
        tracer = observability.get_tracer("service")
        async with tracer.start_span("operation"):
            pass  # No tracing overhead
        ```
    """

    def __init__(self) -> None:
        """Initialize NoOp provider."""
        self._tracer = NoOpTracer()
        self._meter = NoOpMeter()
        self._logger = NoOpLogger()

    def get_tracer(self, name: str) -> NoOpTracer:
        """Get no-op tracer."""
        return self._tracer

    def get_meter(self, name: str) -> NoOpMeter:
        """Get no-op meter."""
        return self._meter

    def get_logger(self, name: str) -> NoOpLogger:
        """Get no-op logger."""
        return self._logger

    async def start(self) -> None:
        """Start (no-op)."""
        pass

    async def stop(self) -> None:
        """Stop (no-op)."""
        pass
