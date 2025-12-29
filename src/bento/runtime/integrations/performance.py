"""Performance monitoring for Bento Runtime."""

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bento.runtime.bootstrap import BentoRuntime

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """Monitors and reports runtime performance metrics."""

    def __init__(self, runtime: "BentoRuntime") -> None:
        """Initialize performance monitor.

        Args:
            runtime: BentoRuntime instance
        """
        self.runtime = runtime
        self._request_count = 0
        self._request_times: list[float] = []

    def get_metrics(self) -> dict[str, float]:
        """Get startup performance metrics.

        Returns:
            Dictionary with startup timing data:
            - total_time: Total startup time in seconds
            - gates_time: Contract validation time
            - register_time: Module registration time
            - database_time: Database setup time

        Example:
            ```python
            metrics = runtime.get_startup_metrics()
            print(f"Total startup: {metrics['total_time']:.2f}s")
            print(f"Gates: {metrics['gates_time']:.3f}s")
            print(f"Modules: {metrics['register_time']:.3f}s")
            print(f"Database: {metrics['database_time']:.3f}s")
            ```
        """
        return self.runtime._startup_metrics.copy()

    def log_metrics(self) -> None:
        """Log startup performance metrics to logger.

        Useful for performance monitoring and optimization.

        Example:
            ```python
            await runtime.build_async()
            runtime.log_startup_metrics()
            # Logs:
            # INFO: Startup metrics: total=0.81s, gates=0.12s, register=0.46s, database=0.23s
            ```
        """
        if not self.runtime._startup_metrics:
            logger.warning("No startup metrics available (runtime not built yet)")
            return

        metrics = self.runtime._startup_metrics
        logger.info(
            f"Startup metrics: "
            f"total={metrics.get('total_time', 0):.2f}s, "
            f"gates={metrics.get('gates_time', 0):.3f}s, "
            f"register={metrics.get('register_time', 0):.3f}s, "
            f"database={metrics.get('database_time', 0):.3f}s"
        )

    def get_runtime_info(self) -> dict[str, Any]:
        """Get comprehensive runtime information.

        Returns:
            Dictionary with runtime information:
            - service_name: Service name
            - environment: Environment (local/dev/prod)
            - modules: Number of registered modules
            - module_names: List of module names
            - built: Whether runtime is built
            - has_database: Whether database is configured
            - has_contracts: Whether contracts are configured

        Example:
            ```python
            info = runtime.get_runtime_info()
            print(f"Service: {info['service_name']}")
            print(f"Modules: {info['modules']}")
            ```
        """
        return {
            "service_name": self.runtime.config.service_name,
            "environment": self.runtime.config.environment,
            "modules": len(self.runtime.registry),
            "module_names": self.runtime.registry.names(),
            "built": self.runtime._built,
            "has_database": self.runtime._session_factory is not None,
            "has_contracts": self.runtime._contracts is not None,
        }

    def record_request(self, duration: float) -> None:
        """Record a request duration for statistics.

        Args:
            duration: Request duration in seconds

        Example:
            ```python
            start = time.time()
            # ... handle request ...
            runtime.performance_monitor.record_request(time.time() - start)
            ```
        """
        self._request_count += 1
        self._request_times.append(duration)

        # Keep only last 1000 requests to avoid memory issues
        if len(self._request_times) > 1000:
            self._request_times = self._request_times[-1000:]

    def get_request_stats(self) -> dict[str, float]:
        """Get request performance statistics.

        Returns:
            Dictionary with request statistics:
            - count: Total number of recorded requests
            - avg_time: Average request time in seconds
            - min_time: Minimum request time in seconds
            - max_time: Maximum request time in seconds

        Example:
            ```python
            stats = runtime.performance_monitor.get_request_stats()
            print(f"Avg response time: {stats['avg_time']:.3f}s")
            ```
        """
        if not self._request_times:
            return {
                "count": 0,
                "avg_time": 0.0,
                "min_time": 0.0,
                "max_time": 0.0,
            }

        return {
            "count": self._request_count,
            "avg_time": sum(self._request_times) / len(self._request_times),
            "min_time": min(self._request_times),
            "max_time": max(self._request_times),
        }
