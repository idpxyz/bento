"""
Memory-based metrics recorder for the observability framework.
This recorder stores metrics in memory for development, testing, and debugging purposes.
"""

import asyncio
import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from pydantic import BaseModel, Field

# Fix circular import by using relative import instead of absolute
from idp.framework.infrastructure.observability.core.config import MetricsConfig
from idp.framework.infrastructure.observability.core.metadata import MetricMetadata
from idp.framework.infrastructure.observability.metrics.recorder import (
    BaseMetricsRecorder,
)

logger = logging.getLogger(__name__)


class MemoryMetricsConfig(MetricsConfig):
    """Configuration for the memory-based metrics recorder."""
    
    max_metrics: int = Field(
        10000, 
        description="Maximum number of metrics to store in memory"
    )
    retention_minutes: int = Field(
        60, 
        description="Number of minutes to retain metrics data (0 for unlimited)"
    )
    flush_interval: float = Field(
        1.0, 
        description="Time in seconds between automatic cleanups"
    )
    enable_statistics: bool = Field(
        True, 
        description="Whether to collect statistics on metrics usage"
    )


class StoredMetric(BaseModel):
    """Model representing a stored metric in memory."""
    
    name: str
    value: float
    labels: Dict[str, str]
    timestamp: datetime


class MetricInstance(BaseModel):
    """Model representing a metric instance with all its recorded values."""
    
    metadata: MetricMetadata
    values: List[StoredMetric] = Field(default_factory=list)
    
    def add_value(self, value: float, labels: Dict[str, str]) -> None:
        """Add a value to this metric instance."""
        self.values.append(
            StoredMetric(
                name=self.metadata.name,
                value=value,
                labels=labels,
                timestamp=datetime.now()
            )
        )


class MemoryMetricsRecorder(BaseMetricsRecorder):
    """
    A metrics recorder that stores metrics in memory.
    
    This recorder implements the IMetricsRecorder interface and extends the BaseMetricsRecorder
    with memory-specific functionality. It's ideal for development, testing, and debugging.
    
    Features:
    - Stores metrics in memory for easy access and inspection
    - Supports retention policies to limit memory usage
    - Provides statistics on metrics usage
    - Simulates the behavior of production recorders but without external dependencies
    
    Usage:
        recorder = MemoryMetricsRecorder(
            service_name="my-service",
            config=MemoryMetricsConfig(
                max_metrics=10000,
                retention_minutes=60
            )
        )
        
        await recorder.initialize()
        await recorder.increment_counter("requests_total", 1, {"endpoint": "/api/users"})
        
        # Get metrics for inspection
        metrics = recorder.get_metrics()
    """
    
    def __init__(
        self,
        service_name: str,
        config: Optional[MemoryMetricsConfig] = None,
        prefix: str = "",
    ):
        """
        Initialize the memory metrics recorder.
        
        Args:
            service_name: The name of the service using this recorder
            config: Memory recorder configuration
            prefix: Optional prefix for all metric names
        """
        super().__init__(service_name=service_name, prefix=prefix)
        self.config = config or MemoryMetricsConfig()
        self._metrics: Dict[str, MetricInstance] = {}
        self._flush_task: Optional[asyncio.Task] = None
        self._statistics: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "last_updated": None}
        )
        self._initialized = False
    
    async def initialize(self) -> None:
        """
        Initialize the memory metrics recorder.
        
        This method:
        1. Registers standard metrics
        2. Starts background tasks for periodic cleanup
        """
        logger.info(f"Initializing memory metrics recorder for service {self.service_name}")
        
        # Register standard metrics
        await self._register_standard_metrics()
        
        # Start background task for cleanup
        self._flush_task = asyncio.create_task(self._periodic_cleanup())
        
        self._initialized = True
        logger.info("Memory metrics recorder initialized successfully")
    
    async def shutdown(self) -> None:
        """
        Shutdown the memory metrics recorder.
        
        This method:
        1. Cancels all background tasks
        2. Clears stored metrics
        """
        logger.info("Shutting down memory metrics recorder")
        
        # Cancel background task
        if self._flush_task and not self._flush_task.done():
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        
        # Clear metrics
        self._metrics.clear()
        self._metrics_cache.clear()
        self._statistics.clear()
        
        self._initialized = False
        logger.info("Memory metrics recorder shut down successfully")
    
    async def register_metric(self, metadata: MetricMetadata) -> None:
        """
        Register a metric in memory.
        
        Args:
            metadata: Metadata for the metric to register
        """
        if not self._initialized:
            logger.warning("Memory metrics recorder not initialized")
        
        # Register in base class
        await super()._register_metric(metadata)
        
        # Store in memory
        prefixed_name = f"{self.prefix}{metadata.name}" if self.prefix else metadata.name
        
        if prefixed_name not in self._metrics:
            self._metrics[prefixed_name] = MetricInstance(metadata=metadata)
    
    async def flush(self) -> None:
        """
        Flush metrics from cache to memory storage.
        
        This method processes all metrics in the cache and stores them in memory.
        """
        if not self._metrics_cache:
            return
        
        logger.debug(f"Flushing {len(self._metrics_cache)} metrics to memory")
        
        start_time = time.time()
        async with self._processing_time_context():
            try:
                # Process each metric in the cache
                for metric_data in self._metrics_cache:
                    prefixed_name = f"{self.prefix}{metric_data['name']}" if self.prefix else metric_data['name']
                    
                    # Ensure metric is registered
                    if prefixed_name not in self._metrics:
                        logger.warning(f"Metric {prefixed_name} not registered, skipping")
                        continue
                    
                    # Add the value to the metric instance
                    self._metrics[prefixed_name].add_value(
                        value=metric_data['value'],
                        labels=metric_data['labels']
                    )
                    
                    # Update statistics
                    if self.config.enable_statistics:
                        self._statistics[prefixed_name]["count"] += 1
                        self._statistics[prefixed_name]["last_updated"] = datetime.now()
                
                # Clear the cache after processing
                self._metrics_cache.clear()
                
                # Check if we've exceeded max_metrics and truncate if necessary
                total_metrics = sum(len(m.values) for m in self._metrics.values())
                if total_metrics > self.config.max_metrics:
                    self._truncate_metrics()
                
            except Exception as e:
                # Increment dropped metrics on error
                await self._increment_dropped_metrics(len(self._metrics_cache))
                logger.error(f"Error flushing metrics to memory: {e}")
        
        logger.debug(f"Metrics flush completed in {time.time() - start_time:.3f}s")
    
    async def query_metric(
        self,
        metric_name: str,
        start_time: datetime,
        end_time: datetime,
        labels: Optional[Dict[str, str]] = None,
        aggregation: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Query metrics from memory.
        
        Args:
            metric_name: Name of the metric to query
            start_time: Start of the time range
            end_time: End of the time range
            labels: Optional filter by labels
            aggregation: Optional aggregation method (sum, avg, min, max, count)
            
        Returns:
            List of metric values matching the query criteria
        """
        prefixed_name = f"{self.prefix}{metric_name}" if self.prefix else metric_name
        
        if prefixed_name not in self._metrics:
            return []
        
        # Get metric values within the time range
        metric_instance = self._metrics[prefixed_name]
        filtered_values = [
            v for v in metric_instance.values
            if start_time <= v.timestamp <= end_time
            and (labels is None or all(v.labels.get(k) == labels[k] for k in labels))
        ]
        
        # Apply aggregation if requested
        if aggregation:
            if not filtered_values:
                return []
            
            # Group by labels
            grouped_values = defaultdict(list)
            for value in filtered_values:
                # Convert labels dict to tuple for grouping
                labels_tuple = tuple(sorted(value.labels.items()))
                grouped_values[labels_tuple].append(value)
            
            results = []
            for labels_tuple, values in grouped_values.items():
                labels_dict = dict(labels_tuple)
                
                if aggregation == "sum":
                    agg_value = sum(v.value for v in values)
                elif aggregation == "avg":
                    agg_value = sum(v.value for v in values) / len(values)
                elif aggregation == "min":
                    agg_value = min(v.value for v in values)
                elif aggregation == "max":
                    agg_value = max(v.value for v in values)
                elif aggregation == "count":
                    agg_value = len(values)
                else:
                    raise ValueError(f"Unsupported aggregation method: {aggregation}")
                
                results.append({
                    "value": agg_value,
                    "labels": labels_dict,
                    "period_start": start_time,
                    "period_end": end_time
                })
            
            return results
        
        # Return raw values
        return [
            {
                "timestamp": v.timestamp,
                "value": v.value,
                "labels": v.labels
            }
            for v in filtered_values
        ]
    
    async def get_metric_metadata(self, metric_name: Optional[str] = None) -> Union[MetricMetadata, List[MetricMetadata]]:
        """
        Get metadata for a specific metric or all metrics.
        
        Args:
            metric_name: Optional name of the metric to retrieve metadata for
                         If None, metadata for all metrics is returned
        
        Returns:
            A single MetricMetadata object or a list of MetricMetadata objects
        """
        if metric_name:
            prefixed_name = f"{self.prefix}{metric_name}" if self.prefix else metric_name
            
            if prefixed_name not in self._metrics:
                raise ValueError(f"Metric {metric_name} not found")
            
            return self._metrics[prefixed_name].metadata
        else:
            # Return all metrics metadata
            return [m.metadata for m in self._metrics.values()]
    
    async def health_check(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Check the health of the memory metrics recorder.
        
        Returns:
            A tuple containing:
            - Boolean indicating if the recorder is healthy
            - Dictionary with health details
        """
        total_metrics = sum(len(m.values) for m in self._metrics.values())
        
        return True, {
            "status": "healthy",
            "total_metrics": total_metrics,
            "distinct_metrics": len(self._metrics),
            "cache_size": len(self._metrics_cache),
            "retention_minutes": self.config.retention_minutes,
            "max_metrics": self.config.max_metrics,
            "usage_percent": (total_metrics / self.config.max_metrics) * 100 if self.config.max_metrics > 0 else 0,
            "statistics": self._statistics if self.config.enable_statistics else None,
        }
    
    def get_metrics(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all metrics stored in memory.
        
        Returns:
            A dictionary mapping metric names to lists of stored values
        """
        result = {}
        for name, metric_instance in self._metrics.items():
            result[name] = [
                {
                    "value": v.value,
                    "labels": v.labels,
                    "timestamp": v.timestamp
                }
                for v in metric_instance.values
            ]
        return result
    
    def get_metric_values(self, metric_name: str) -> List[Dict[str, Any]]:
        """
        Get all values for a specific metric.
        
        Args:
            metric_name: Name of the metric to retrieve values for
            
        Returns:
            List of dictionaries with value, labels, and timestamp
        """
        prefixed_name = f"{self.prefix}{metric_name}" if self.prefix else metric_name
        
        if prefixed_name not in self._metrics:
            return []
        
        return [
            {
                "value": v.value,
                "labels": v.labels,
                "timestamp": v.timestamp
            }
            for v in self._metrics[prefixed_name].values
        ]
    
    def get_statistics(self) -> Dict[str, Dict[str, Any]]:
        """
        Get usage statistics for all metrics.
        
        Returns:
            Dictionary mapping metric names to statistics
        """
        if not self.config.enable_statistics:
            return {}
        
        return dict(self._statistics)
    
    def clear_metrics(self) -> None:
        """Clear all stored metrics."""
        for metric_instance in self._metrics.values():
            metric_instance.values.clear()
    
    def clear_metric(self, metric_name: str) -> None:
        """
        Clear all values for a specific metric.
        
        Args:
            metric_name: Name of the metric to clear
        """
        prefixed_name = f"{self.prefix}{metric_name}" if self.prefix else metric_name
        
        if prefixed_name in self._metrics:
            self._metrics[prefixed_name].values.clear()
    
    # Internal methods
    
    async def _periodic_cleanup(self) -> None:
        """Background task for cleaning up old metrics data."""
        while True:
            try:
                await asyncio.sleep(self.config.flush_interval)
                
                # Flush any pending metrics
                await self.flush()
                
                # Skip cleanup if retention is disabled
                if self.config.retention_minutes <= 0:
                    continue
                
                # Clean up old metrics
                retention_threshold = datetime.now() - timedelta(minutes=self.config.retention_minutes)
                
                for metric_instance in self._metrics.values():
                    # Filter out old values
                    original_length = len(metric_instance.values)
                    metric_instance.values = [
                        v for v in metric_instance.values
                        if v.timestamp >= retention_threshold
                    ]
                    removed = original_length - len(metric_instance.values)
                    
                    if removed > 0:
                        logger.debug(f"Removed {removed} old values for metric {metric_instance.metadata.name}")
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
    
    def _truncate_metrics(self) -> None:
        """Truncate the oldest metrics to stay within max_metrics limit."""
        # Calculate how many metrics to remove
        total_metrics = sum(len(m.values) for m in self._metrics.values())
        to_remove = total_metrics - self.config.max_metrics
        
        if to_remove <= 0:
            return
        
        logger.debug(f"Truncating {to_remove} metrics to stay within limit")
        
        # Collect all metrics with timestamps for sorting
        all_metrics = []
        for name, metric_instance in self._metrics.items():
            for i, value in enumerate(metric_instance.values):
                all_metrics.append((name, i, value.timestamp))
        
        # Sort by timestamp (oldest first)
        all_metrics.sort(key=lambda x: x[2])
        
        # Remove the oldest metrics
        for name, index, _ in all_metrics[:to_remove]:
            # Convert from absolute index to relative
            rel_index = index
            for i, (prev_name, prev_idx, _) in enumerate(all_metrics[:to_remove]):
                if prev_name == name and prev_idx < index:
                    rel_index -= 1
            
            # Remove the metric at the relative index
            if 0 <= rel_index < len(self._metrics[name].values):
                self._metrics[name].values.pop(rel_index)
    
    async def _add_to_cache(self, name: str, value: float, labels: Dict[str, str]) -> None:
        """Add a metric to the cache and flush if the batch size is reached."""
        await super()._add_to_cache(name, value, labels)
        
        # Check if we're approaching max_metrics and flush if so
        total_metrics = sum(len(m.values) for m in self._metrics.values())
        if total_metrics + len(self._metrics_cache) >= self.config.max_metrics:
            await self.flush() 