"""Cache Statistics - Cache performance monitoring.

This module provides cache statistics for monitoring and optimization.
"""

import time
from dataclasses import dataclass, field


@dataclass
class CacheStats:
    """Cache statistics for monitoring.

    Tracks cache operations and calculates performance metrics.

    Attributes:
        hits: Number of cache hits
        misses: Number of cache misses
        sets: Number of cache writes
        deletes: Number of cache deletions
        errors: Number of cache errors
        total_get_time: Total time spent on get operations (seconds)
        total_set_time: Total time spent on set operations (seconds)

    Example:
        ```python
        stats = CacheStats()

        # Record operations
        stats.record_hit()
        stats.record_miss()
        stats.record_set()

        # Get metrics
        print(f"Hit rate: {stats.hit_rate:.2%}")
        print(f"Total operations: {stats.total_operations}")
        print(f"Average get time: {stats.avg_get_time:.4f}s")
        ```
    """

    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    errors: int = 0
    total_get_time: float = 0.0
    total_set_time: float = 0.0
    _last_reset: float = field(default_factory=time.time)

    @property
    def total_operations(self) -> int:
        """Total number of operations.

        Returns:
            Sum of all operations
        """
        return self.hits + self.misses + self.sets + self.deletes

    @property
    def get_operations(self) -> int:
        """Total number of get operations.

        Returns:
            Sum of hits and misses
        """
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:
        """Cache hit rate.

        Returns:
            Hit rate as a decimal (0.0 to 1.0)

        Example:
            ```python
            if stats.hit_rate > 0.8:
                print("Good cache performance!")
            ```
        """
        if self.get_operations == 0:
            return 0.0
        return self.hits / self.get_operations

    @property
    def miss_rate(self) -> float:
        """Cache miss rate.

        Returns:
            Miss rate as a decimal (0.0 to 1.0)
        """
        return 1.0 - self.hit_rate

    @property
    def avg_get_time(self) -> float:
        """Average get operation time.

        Returns:
            Average time in seconds
        """
        if self.get_operations == 0:
            return 0.0
        return self.total_get_time / self.get_operations

    @property
    def avg_set_time(self) -> float:
        """Average set operation time.

        Returns:
            Average time in seconds
        """
        if self.sets == 0:
            return 0.0
        return self.total_set_time / self.sets

    @property
    def uptime(self) -> float:
        """Time since last reset.

        Returns:
            Uptime in seconds
        """
        return time.time() - self._last_reset

    def record_hit(self, duration: float = 0.0) -> None:
        """Record a cache hit.

        Args:
            duration: Time taken for the operation
        """
        self.hits += 1
        self.total_get_time += duration

    def record_miss(self, duration: float = 0.0) -> None:
        """Record a cache miss.

        Args:
            duration: Time taken for the operation
        """
        self.misses += 1
        self.total_get_time += duration

    def record_set(self, duration: float = 0.0) -> None:
        """Record a cache set operation.

        Args:
            duration: Time taken for the operation
        """
        self.sets += 1
        self.total_set_time += duration

    def record_delete(self) -> None:
        """Record a cache delete operation."""
        self.deletes += 1

    def record_error(self) -> None:
        """Record a cache error."""
        self.errors += 1

    def reset(self) -> None:
        """Reset all statistics.

        Example:
            ```python
            # Reset daily stats
            stats.reset()
            ```
        """
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.deletes = 0
        self.errors = 0
        self.total_get_time = 0.0
        self.total_set_time = 0.0
        self._last_reset = time.time()

    def to_dict(self) -> dict[str, float | int]:
        """Convert stats to dictionary.

        Returns:
            Dictionary with all statistics

        Example:
            ```python
            stats_dict = stats.to_dict()
            print(json.dumps(stats_dict, indent=2))
            ```
        """
        return {
            "hits": self.hits,
            "misses": self.misses,
            "sets": self.sets,
            "deletes": self.deletes,
            "errors": self.errors,
            "total_operations": self.total_operations,
            "get_operations": self.get_operations,
            "hit_rate": self.hit_rate,
            "miss_rate": self.miss_rate,
            "avg_get_time": self.avg_get_time,
            "avg_set_time": self.avg_set_time,
            "uptime": self.uptime,
        }

    def __repr__(self) -> str:
        """String representation of stats."""
        return (
            f"CacheStats(hits={self.hits}, misses={self.misses}, "
            f"hit_rate={self.hit_rate:.2%}, operations={self.total_operations})"
        )
