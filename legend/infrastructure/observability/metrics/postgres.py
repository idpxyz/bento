#!/usr/bin/env python3
"""
PostgreSQL Metrics Recorder for IDP Observability Framework

This module provides a PostgreSQL implementation of the IMetricsRecorder interface
for persisting metrics data to a PostgreSQL database.
"""

import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Set, Union, cast

from sqlalchemy import text

from idp.framework.infrastructure.database.core.database import Database, DatabaseConfig
from idp.framework.infrastructure.database.core.factory import DatabaseFactory
from idp.framework.infrastructure.database.core.transaction import TransactionContext

from ..core.config import MetricsConfig, PostgresCommonConfig
from ..core.constants import (
    METRIC_TYPE_COUNTER,
    METRIC_TYPE_GAUGE,
    METRIC_TYPE_HISTOGRAM,
    METRIC_TYPE_SUMMARY,
)
from ..core.interfaces import IMetricsRecorder
from ..core.metadata import MetricMetadata, StandardMetrics
from .recorder import BaseMetricsRecorder

logger = logging.getLogger(__name__)


class PostgresMetricsRecorder(BaseMetricsRecorder):
    """PostgreSQL implementation of the IMetricsRecorder interface."""

    def __init__(
        self,
        postgres_config: PostgresCommonConfig,
        service_name: str,
        namespace: str = "app",
        metric_prefix: str = "",
        flush_interval: float = 60.0,
        batch_size: int = 100,
        max_queue_size: int = 10000,
        metrics_table: str = "metrics",
        metadata_table: str = "metric_metadata",
        default_labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """Initialize the PostgreSQL metrics recorder."""
        super().__init__(prefix=metric_prefix, default_labels=default_labels or {
            "service": service_name,
            "namespace": namespace
        })
        
        self.postgres_config = postgres_config
        self.service_name = service_name
        self.namespace = namespace
        self.flush_interval = flush_interval
        self.batch_size = batch_size
        self.max_queue_size = max_queue_size
        self.schema_name = postgres_config.schema
        self.metrics_table = f"{self.schema_name}.{metrics_table}"
        self.metadata_table = f"{self.schema_name}.{metadata_table}"
        
        self._db: Optional[Database] = None
        self._flush_task: Optional[asyncio.Task] = None
        self._is_flushing = False
        self._registered_metric_names: Set[str] = set()

    async def _get_db(self) -> Database:
        """Get database instance with lazy initialization."""
            
        db_config = DatabaseConfig( 
            type="postgresql",
            connection={
                "host": connection_info["host"],
                "port": int(connection_info["port"]),
                "database": connection_info["database"],
                "db_schema": self.schema_name
            },
            credentials={
                "username": connection_info["user"],
                "password": connection_info["password"]
            },
            pool={
                "min_size": self.postgres_config.pool_min_size,
                "max_size": self.postgres_config.pool_max_size,
                "max_queries": 50000,
                "timeout": 30
            },
            monitor={
                "enable_metrics": True,
                "slow_query_threshold": self.postgres_config.slow_query_threshold,
                "log_slow_queries": True
            }
        )
        DatabaseFactory.register_database(db_config.type)
        
        db = await DatabaseFactory.get_database(db_config, "postgres-metrics-recorder")
        return db

    @asynccontextmanager
    async def _transaction(self) -> TransactionContext:
        """Get a database transaction context."""
        db = await self._get_db()
        async with db.transaction() as tx:
            yield tx

    async def initialize(self) -> None:
        """Initialize the recorder."""
        try:
            logger.info(f"Initializing PostgreSQL metrics recorder for {self.service_name}")
            
            # Initialize database
            db = await self._get_db()
            await DatabaseFactory.initialize_all()
            
            # Check health
            health_status = await DatabaseFactory.check_all_health()
            if not health_status or not all(health_status.values()):
                unhealthy_dbs = [name for name, status in health_status.items() if not status]
                raise Exception(f"Database health check failed for: {', '.join(unhealthy_dbs)}")
            
            # Setup schema and tables
            await self._ensure_schema_exists()
            await self._register_standard_metrics()
            
            # Start background flush
            if self.flush_interval > 0:
                self._flush_task = asyncio.create_task(self._background_flush())
                logger.debug(f"Started background flush task with interval: {self.flush_interval}s")
            
            logger.info("PostgreSQL metrics recorder initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize: {e}", exc_info=True)
            await self.shutdown()
            raise

    async def _register_metric(self, metadata: MetricMetadata) -> None:
        """Register a metric."""
        if metadata.name in self._registered_metric_names:
            return
            
        try:
            async with self._transaction() as tx:
                # Check if metric exists
                result = await tx.execute_query(
                    text(f"SELECT id FROM {self.metadata_table} WHERE name = :name"),
                    {"name": metadata.name}
                )
                existing = result.scalar()
                
                params = {
                    "name": metadata.name,
                    "help": metadata.help,
                    "type": metadata.type,
                    "unit": metadata.unit,
                    "label_names": metadata.label_names,
                    "buckets": metadata.buckets,
                    "objectives": json.dumps(metadata.objectives) if metadata.objectives else None,
                    "alert_threshold": metadata.alert_threshold
                }
                
                if existing:
                    await tx.execute_query(
                        text(f"""
                        UPDATE {self.metadata_table}
                        SET help = :help, type = :type, unit = :unit,
                            label_names = :label_names, buckets = :buckets,
                            objectives = :objectives, alert_threshold = :alert_threshold,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE name = :name
                        """),
                        params
                    )
                else:
                    await tx.execute_query(
                        text(f"""
                        INSERT INTO {self.metadata_table}
                        (name, help, type, unit, label_names, buckets, objectives, alert_threshold)
                        VALUES (:name, :help, :type, :unit, :label_names, :buckets, :objectives, :alert_threshold)
                        """),
                        params
                    )
                
                self._registered_metric_names.add(metadata.name)
                logger.debug(f"Registered metric: {metadata.name}")
                
        except Exception as e:
            logger.error(f"Failed to register metric {metadata.name}: {e}", exc_info=True)
            raise

    async def _flush_metrics(self, metrics: List[Dict[str, Any]]) -> None:
        """Flush metrics to database."""
        if not metrics:
            return
            
        try:
            async with self._transaction() as tx:
                for i in range(0, len(metrics), self.batch_size):
                    batch = metrics[i:i + self.batch_size]
                    await tx.execute_query(
                        text(f"""
                        INSERT INTO {self.metrics_table}
                        (name, value, labels, timestamp)
                        VALUES (:name, :value, :labels, CURRENT_TIMESTAMP)
                        """),
                        [
                            {
                                "name": metric["name"],
                                "value": metric["value"],
                                "labels": json.dumps(metric["labels"])
                            }
                            for metric in batch
                        ]
                    )
        except Exception as e:
            logger.error(f"Failed to flush metrics: {e}", exc_info=True)
            raise

    async def _check_health(self) -> bool:
        """Check recorder health."""
        try:
            db = await self._get_db()
            result = await db.execute_query(text("SELECT 1"))
            return bool(result.scalar())
        except Exception as e:
            logger.error(f"Health check failed: {e}", exc_info=True)
            return False

    async def shutdown(self) -> None:
        """Shutdown the recorder."""
        logger.info("Shutting down PostgreSQL metrics recorder")
        
        try:
            if self._flush_task:
                self._flush_task.cancel()
                try:
                    await self._flush_task
                except asyncio.CancelledError:
                    pass
            
            if self._metrics_cache:
                await self.flush()
            
            await DatabaseFactory.cleanup_all()
            self._db = None
            
            logger.info("PostgreSQL metrics recorder shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)
            raise

    async def _ensure_schema_exists(self) -> None:
        """Ensure the database schema and tables exist."""
        if not self._db:
            raise RuntimeError("Database not initialized")
            
        try:
            # Create schema if not exists
            await self._db.execute_query(text(f"CREATE SCHEMA IF NOT EXISTS {self.schema_name}"))
            
            # Create metadata table if not exists
            await self._db.execute_query(text(f"""
                CREATE TABLE IF NOT EXISTS {self.metadata_table} (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    help TEXT,
                    type VARCHAR(50) NOT NULL,
                    unit VARCHAR(50),
                    label_names TEXT[] DEFAULT '{{}}',
                    buckets FLOAT[] DEFAULT NULL,
                    objectives JSONB DEFAULT NULL,
                    alert_threshold FLOAT DEFAULT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(name)
                )
            """))
            
            # Create metrics table if not exists
            await self._db.execute_query(text(f"""
                CREATE TABLE IF NOT EXISTS {self.metrics_table} (
                    id BIGSERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    value DOUBLE PRECISION NOT NULL,
                    labels JSONB DEFAULT '{{}}'::jsonb,
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Create indexes
            await self._create_indexes()
            
            logger.debug(f"Ensured schema and tables exist in {self.schema_name}")
            
        except Exception as e:
            logger.error(f"Error ensuring schema exists: {e}", exc_info=True)
            raise
            
    async def _create_indexes(self) -> None:
        """Create necessary indexes for performance optimization."""
        try:
            # Create indexes if they don't exist
            index_queries = [
                f"""
                CREATE INDEX IF NOT EXISTS idx_metric_metadata_name 
                ON {self.metadata_table}(name)
                """,
                f"""
                CREATE INDEX IF NOT EXISTS idx_metrics_timestamp 
                ON {self.metrics_table} USING BRIN(timestamp)
                """,
                f"""
                CREATE INDEX IF NOT EXISTS idx_metrics_name 
                ON {self.metrics_table}(name)
                """,
                f"""
                CREATE INDEX IF NOT EXISTS idx_metrics_labels 
                ON {self.metrics_table} USING GIN(labels)
                """
            ]
            
            for query in index_queries:
                await self._db.execute_query(text(query))
                
        except Exception as e:
            logger.error(f"Error creating indexes: {e}", exc_info=True)
            raise
    
    async def _register_standard_metrics(self) -> None:
        """Register standard metrics in the database."""
        for metric in StandardMetrics.get_all_metrics():
            await self._register_metric(metric)
    
    async def _background_flush(self) -> None:
        """Background task to periodically flush metrics."""
        while True:
            try:
                await asyncio.sleep(self.flush_interval)
                if self._metrics_cache:
                    await self.flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in background flush: {e}", exc_info=True)
                await asyncio.sleep(1)  # Brief pause before retrying
    
    async def flush(self) -> None:
        """Flush pending metrics to the database."""
        if self._is_flushing or not self._db:
            return
            
        self._is_flushing = True
        metrics_to_flush = []
        
        try:
            # Get metrics from cache
            with self._cache_lock:
                if not self._metrics_cache:
                    return
                    
                metrics_to_flush = list(self._metrics_cache.values())
                self._metrics_cache.clear()
            
            if not metrics_to_flush:
                return
                
            # Measure flush time
            start_time = time.monotonic()
            
            # Flush metrics in batches
            for i in range(0, len(metrics_to_flush), self.batch_size):
                batch = metrics_to_flush[i:i + self.batch_size]
                await self._flush_batch(batch)
            
            # Record flush time
            flush_time = time.monotonic() - start_time
            self._add_to_cache({
                "name": self._format_metric_name(self.METRICS_PROCESSING_DURATION),
                "value": flush_time,
                "labels": {"operation": "flush"},
            })
            
            logger.debug(f"Flushed {len(metrics_to_flush)} metrics in {flush_time:.3f}s")
            
        except Exception as e:
            logger.error(f"Error flushing metrics: {e}", exc_info=True)
            # Count dropped metrics
            self._add_to_cache({
                "name": self._format_metric_name(self.DROPPED_METRICS),
                "value": len(metrics_to_flush),
                "labels": {"reason": "flush_error"},
            })
        finally:
            self._is_flushing = False
    
    async def _flush_batch(self, metrics: List[Dict[str, Any]]) -> None:
        """Flush a batch of metrics to the database.
        
        Args:
            metrics: List of metrics to flush
        """
        if not metrics:
            return
            
        try:
            await self._flush_metrics(metrics)
        except Exception as e:
            logger.error(f"Error flushing batch: {e}", exc_info=True)
            raise
    
    async def batch_record(self, metrics: List[Dict[str, Any]]) -> None:
        """Record multiple metrics at once.
        
        Args:
            metrics: List of metrics to record
        """
        for metric in metrics:
            name = metric.get("name", "")
            value = metric.get("value", 0)
            labels = metric.get("labels", {})
            metric_type = metric.get("type", METRIC_TYPE_GAUGE)
            
            try:
                if metric_type == METRIC_TYPE_COUNTER:
                    await self.increment_counter(name, value, labels)
                elif metric_type == METRIC_TYPE_GAUGE:
                    await self.set_gauge(name, value, labels)
                elif metric_type == METRIC_TYPE_HISTOGRAM:
                    await self.observe_histogram(name, value, labels)
                elif metric_type == METRIC_TYPE_SUMMARY:
                    await self.observe_summary(name, value, labels)
                else:
                    logger.warning(f"Unknown metric type: {metric_type} for metric: {name}")
            except Exception as e:
                logger.error(f"Error recording metric {name}: {e}", exc_info=True)
    
    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the metrics recorder.
        
        Returns:
            Dict with health status information
        """
        status = {
            "status": "unknown",
            "details": {
                "connection": "not_initialized",
                "cache_size": len(self._metrics_cache),
                "registered_metrics": len(self._registered_metric_names),
                "is_flushing": self._is_flushing,
                "flush_interval": self.flush_interval,
                "batch_size": self.batch_size,
            }
        }
        
        if not self._db:
            status["status"] = "unhealthy"
            status["details"]["connection"] = "not_initialized"
            return status
        
        try:
            # Test connection
            result = await self._db.execute_query(text("SELECT 1"))
            if result.scalar():
                status["status"] = "healthy"
                status["details"]["connection"] = "connected"
            
            # Add flush task status
            if self._flush_task:
                status["details"]["flush_task"] = {
                    "status": "running" if not self._flush_task.done() else "stopped",
                    "done": self._flush_task.done(),
                    "cancelled": self._flush_task.cancelled() if self._flush_task.done() else False
                }
            
        except Exception as e:
            status["status"] = "unhealthy"
            status["details"]["error"] = str(e)
            status["details"]["connection"] = "error"
            logger.error(f"Health check failed: {e}", exc_info=True)
        
        return status
    
    @classmethod
    def from_config(cls, config: MetricsConfig, **kwargs: Any) -> IMetricsRecorder:
        """Create a PostgresMetricsRecorder from configuration.
        
        Args:
            config: The metrics configuration
            **kwargs: Additional arguments to pass to the constructor
            
        Returns:
            A configured PostgresMetricsRecorder instance
        """
        if not config.postgres or not config.postgres.common:
            raise ValueError("PostgreSQL configuration is required")
        
        recorder = cls(
            postgres_config=config.postgres.common,
            service_name=config.service_name,
            namespace=config.namespace,
            metric_prefix=config.prefix,
            flush_interval=config.aggregation_interval,
            batch_size=kwargs.get("batch_size", 100),
            max_queue_size=kwargs.get("max_queue_size", 10000),
            metrics_table=config.postgres.metrics_table,
            metadata_table=config.postgres.metrics_metadata_table,
        )
        
        return cast(IMetricsRecorder, recorder) 