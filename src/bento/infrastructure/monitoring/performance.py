"""Performance monitoring and optimization utilities for Outbox system.

This module provides:
- Database connection pool monitoring
- Query performance analysis
- Resource usage tracking
- Performance optimization suggestions
"""

import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.pool import QueuePool

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics collection."""

    # Database metrics
    active_connections: int = 0
    idle_connections: int = 0
    connection_pool_size: int = 0
    connection_pool_overflow: int = 0

    # Query metrics
    avg_query_time_ms: float = 0.0
    slow_queries_count: int = 0
    total_queries: int = 0

    # Outbox specific metrics
    pending_events: int = 0
    failed_events: int = 0
    events_per_second: float = 0.0

    # Resource metrics
    estimated_memory_usage_kb: float = 0.0
    cpu_usage_percent: float = 0.0

    timestamp: datetime = datetime.now()


class PerformanceMonitor:
    """🔍 Performance monitoring for Outbox and MessageBus systems.

    Features:
    - Real-time connection pool monitoring
    - Query performance tracking
    - Resource usage analysis
    - Performance bottleneck detection
    """

    def __init__(self, session_factory):
        self.session_factory = session_factory
        self._query_times: list[float] = []
        self._last_metrics_time = time.time()
        self._events_processed = 0

    async def get_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics."""
        metrics = PerformanceMetrics()

        # Database connection pool metrics
        try:
            engine = self.session_factory.get_bind()
            if hasattr(engine.pool, "size"):
                pool = engine.pool
                metrics.connection_pool_size = pool.size()
                metrics.connection_pool_overflow = pool.overflow()

                if isinstance(pool, QueuePool):
                    metrics.active_connections = pool.checked_in()
                    metrics.idle_connections = pool.checked_out()
        except Exception as e:
            logger.warning("Failed to get connection pool metrics: %s", e)

        # Query performance metrics
        if self._query_times:
            metrics.avg_query_time_ms = sum(self._query_times) / len(self._query_times) * 1000
            metrics.slow_queries_count = len(
                [t for t in self._query_times if t > 1.0]
            )  # >1s queries
            metrics.total_queries = len(self._query_times)

        # Outbox specific metrics
        async with self.session_factory() as session:
            try:
                # Pending events
                result = await session.execute(
                    text("SELECT COUNT(*) FROM outbox WHERE status IN ('NEW', 'FAILED')")
                )
                metrics.pending_events = result.scalar() or 0

                # Failed events
                result = await session.execute(
                    text("SELECT COUNT(*) FROM outbox WHERE status = 'FAILED'")
                )
                metrics.failed_events = result.scalar() or 0

            except Exception as e:
                logger.warning("Failed to get outbox metrics: %s", e)

        # Events per second calculation
        current_time = time.time()
        time_diff = current_time - self._last_metrics_time
        if time_diff > 0:
            metrics.events_per_second = self._events_processed / time_diff

        # Reset counters
        self._last_metrics_time = current_time
        self._events_processed = 0
        self._query_times = self._query_times[-100:]  # Keep last 100 query times

        return metrics

    @asynccontextmanager
    async def track_query_time(self):
        """Context manager to track query execution time."""
        start_time = time.time()
        try:
            yield
        finally:
            execution_time = time.time() - start_time
            self._query_times.append(execution_time)

            # Log slow queries
            if execution_time > 1.0:  # >1 second
                logger.warning("Slow query detected: %.2f seconds", execution_time)

    def record_events_processed(self, count: int):
        """Record number of events processed."""
        self._events_processed += count

    async def analyze_performance_bottlenecks(self) -> dict[str, Any]:
        """Analyze system for performance bottlenecks.

        Returns:
            Dictionary with bottleneck analysis and recommendations
        """
        metrics = await self.get_metrics()
        analysis = {
            "bottlenecks": [],
            "recommendations": [],
            "severity": "low",  # low, medium, high, critical
            "metrics": metrics,
        }

        # Connection pool analysis
        if metrics.connection_pool_size > 0:
            pool_usage = (metrics.active_connections / metrics.connection_pool_size) * 100
            if pool_usage > 80:
                analysis["bottlenecks"].append(f"High connection pool usage: {pool_usage:.1f}%")
                analysis["recommendations"].append(
                    "Consider increasing connection pool size or reducing query frequency"
                )
                analysis["severity"] = "high"
            elif pool_usage > 60:
                analysis["bottlenecks"].append(f"Moderate connection pool usage: {pool_usage:.1f}%")
                analysis["recommendations"].append("Monitor connection pool usage trends")
                if analysis["severity"] == "low":
                    analysis["severity"] = "medium"

        # Query performance analysis
        if metrics.avg_query_time_ms > 500:  # >500ms average
            analysis["bottlenecks"].append(
                f"Slow average query time: {metrics.avg_query_time_ms:.1f}ms"
            )
            analysis["recommendations"].append(
                "Review and optimize database queries, consider adding indexes"
            )
            analysis["severity"] = "high"

        if metrics.slow_queries_count > 0:
            slow_query_rate = (metrics.slow_queries_count / metrics.total_queries) * 100
            if slow_query_rate > 10:  # >10% slow queries
                analysis["bottlenecks"].append(f"High slow query rate: {slow_query_rate:.1f}%")
                analysis["recommendations"].append(
                    "Investigate and optimize slow queries immediately"
                )
                analysis["severity"] = "critical"

        # Outbox backlog analysis
        if metrics.pending_events > 10000:
            analysis["bottlenecks"].append(f"Large event backlog: {metrics.pending_events} events")
            analysis["recommendations"].append(
                "Increase OutboxProjector batch size or concurrent projectors"
            )
            analysis["severity"] = "high"

        # Processing rate analysis
        if metrics.events_per_second < 10 and metrics.pending_events > 100:
            analysis["bottlenecks"].append(
                f"Low processing rate: {metrics.events_per_second:.1f} events/sec"
            )
            analysis["recommendations"].append(
                "Optimize OutboxProjector configuration or investigate processing delays"
            )
            if analysis["severity"] in ["low", "medium"]:
                analysis["severity"] = "medium"

        return analysis

    async def get_database_stats(self) -> dict[str, Any]:
        """Get detailed database statistics."""
        stats = {}

        async with self.session_factory() as session:
            try:
                # Table sizes
                result = await session.execute(text("SELECT COUNT(*) as total_records FROM outbox"))
                stats["total_records"] = result.scalar() or 0

                # Status distribution
                result = await session.execute(
                    text("""
                    SELECT status, COUNT(*) as count
                    FROM outbox
                    GROUP BY status
                    """)
                )
                stats["status_distribution"] = {row.status: row.count for row in result}

                # Tenant distribution
                result = await session.execute(
                    text("""
                    SELECT tenant_id, COUNT(*) as count
                    FROM outbox
                    GROUP BY tenant_id
                    ORDER BY count DESC
                    LIMIT 10
                    """)
                )
                stats["tenant_distribution"] = {row.tenant_id: row.count for row in result}

                # Age analysis
                result = await session.execute(
                    text("""
                    SELECT
                        COUNT(*) as old_records
                    FROM outbox
                    WHERE created_at < NOW() - INTERVAL '24 hours'
                    """)
                )
                stats["old_records_24h"] = result.scalar() or 0

                # Index usage (PostgreSQL specific - will be empty for SQLite)
                try:
                    result = await session.execute(
                        text("""
                        SELECT
                            indexname,
                            idx_scan,
                            idx_tup_read,
                            idx_tup_fetch
                        FROM pg_stat_user_indexes
                        WHERE relname = 'outbox'
                        """)
                    )
                    stats["index_usage"] = [
                        {
                            "name": row.indexname,
                            "scans": row.idx_scan,
                            "tuples_read": row.idx_tup_read,
                            "tuples_fetched": row.idx_tup_fetch,
                        }
                        for row in result
                    ]
                except Exception:
                    stats["index_usage"] = []  # Not PostgreSQL or no permissions

            except Exception as e:
                logger.warning("Failed to get database stats: %s", e)
                stats["error"] = str(e)

        return stats


async def cleanup_old_outbox_records(
    session_factory, retention_days: int = 7, batch_size: int = 1000, dry_run: bool = True
) -> dict[str, int]:
    """Clean up old outbox records to improve performance.

    Args:
        session_factory: SQLAlchemy session factory
        retention_days: Number of days to retain records
        batch_size: Number of records to delete per batch
        dry_run: If True, only count records without deleting

    Returns:
        Dictionary with cleanup statistics
    """
    cutoff_date = datetime.now() - timedelta(days=retention_days)
    stats = {"total_candidates": 0, "deleted": 0, "batches": 0}

    async with session_factory() as session:
        # Count candidates
        result = await session.execute(
            text("""
            SELECT COUNT(*)
            FROM outbox
            WHERE status = 'PUBLISHED'
            AND created_at < :cutoff_date
            """),
            {"cutoff_date": cutoff_date},
        )
        stats["total_candidates"] = result.scalar() or 0

        if dry_run:
            logger.info(
                "DRY RUN: Found %d records older than %d days for cleanup",
                stats["total_candidates"],
                retention_days,
            )
            return stats

        # Delete in batches
        while True:
            result = await session.execute(
                text("""
                DELETE FROM outbox
                WHERE id IN (
                    SELECT id FROM outbox
                    WHERE status = 'PUBLISHED'
                    AND created_at < :cutoff_date
                    LIMIT :batch_size
                )
                """),
                {"cutoff_date": cutoff_date, "batch_size": batch_size},
            )

            deleted_count = result.rowcount
            if deleted_count == 0:
                break

            stats["deleted"] += deleted_count
            stats["batches"] += 1

            await session.commit()
            logger.info(
                "Deleted batch %d: %d records (%d total so far)",
                stats["batches"],
                deleted_count,
                stats["deleted"],
            )

    return stats
