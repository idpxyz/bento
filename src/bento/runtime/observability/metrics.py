"""Metrics collection and monitoring."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bento.runtime.bootstrap import BentoRuntime


class MetricsCollector:
    """Collects and manages runtime metrics."""

    def __init__(self) -> None:
        """Initialize metrics collector."""
        self._metrics: dict[str, float] = {}

    def record(self, name: str, value: float) -> None:
        """Record a metric value.

        Args:
            name: Metric name
            value: Metric value
        """
        self._metrics[name] = value

    def get_all(self) -> dict[str, float]:
        """Get all recorded metrics.

        Returns:
            Dictionary of metrics
        """
        return self._metrics.copy()

    def get(self, name: str) -> float | None:
        """Get a specific metric value.

        Args:
            name: Metric name

        Returns:
            Metric value or None if not found
        """
        return self._metrics.get(name)
