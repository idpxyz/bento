#!/usr/bin/env python3
"""
Example demonstrating the usage of PostgreSQL metrics recorder with FastAPI.

This example shows:
1. How to initialize the PostgreSQL metrics recorder
2. How to record different types of metrics
3. How to integrate with FastAPI middleware
4. How to view recorded metrics

Usage:
    uvicorn postgres_metrics_example:app --reload
"""

import asyncio
import logging
import random
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import asyncpg
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from idp.framework.infrastructure.observability.core.config import (
    MetricsConfig,
    ObservabilityConfig,
)
from idp.framework.infrastructure.observability.core.metadata import (
    MetricMetadata,
    MetricType,
    StandardMetrics,
)
from idp.framework.infrastructure.observability.metrics.postgres import (
    PostgresMetricsConfig,
    PostgresMetricsRecorder,
)
from idp.framework.infrastructure.observability.metrics.recorder import (
    BaseMetricsRecorder,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Configuration
POSTGRES_DSN = "postgresql://postgres:postgres@localhost:5432/metrics"
SERVICE_NAME = "postgres-metrics-example"


class MetricResponse(BaseModel):
    """Schema for metric response"""
    metric_name: str
    metric_type: str
    metric_value: float
    labels: Dict[str, str] = Field(default_factory=dict)
    timestamp: str


class AggregatedMetricResponse(BaseModel):
    """Schema for aggregated metric response"""
    metric_name: str
    metric_type: str
    min_value: float
    max_value: float
    avg_value: float
    sum_value: float
    count_value: int
    labels: Dict[str, str] = Field(default_factory=dict)
    timestamp: str
    window_seconds: int


class QueryMetricsRequest(BaseModel):
    metric_name: str
    start_time: datetime
    end_time: datetime
    labels: Optional[Dict[str, str]] = None
    aggregation: Optional[str] = None


class MetricDataPoint(BaseModel):
    timestamp: Optional[datetime] = None
    value: float
    labels: Dict[str, str]
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


class HealthCheckResponse(BaseModel):
    healthy: bool
    details: Dict[str, Any]


metrics_recorder: Optional[PostgresMetricsRecorder] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for setting up and tearing down the metrics recorder"""
    global metrics_recorder
    
    logger.info("Initializing PostgreSQL metrics recorder")
    
    # Create metrics configuration
    postgres_config = PostgresMetricsConfig(
        dsn=POSTGRES_DSN,
        pool_size=5,
        max_inactive_connection_lifetime=300,
        batch_size=100,
        flush_interval=10,
        retention_days=7,
        aggregation_interval=60
    )
    
    metrics_config = MetricsConfig(
        service_name=SERVICE_NAME,
        enabled=True,
        push_gateway_url=None,
        push_interval=15,
        default_labels={"environment": "development"}
    )
    
    # Create and initialize metrics recorder
    metrics_recorder = PostgresMetricsRecorder(
        config=metrics_config,
        postgres_config=postgres_config
    )
    
    # Custom metrics registration
    custom_metric = MetricMetadata(
        name="custom_random_value",
        type=MetricType.GAUGE,
        help="A random value between 0 and 100",
        unit="units",
        label_names=["category"],
        alert_threshold=90.0
    )
    await metrics_recorder.register_metric(custom_metric)
    
    # Initialize the recorder
    await metrics_recorder.initialize()
    
    # Start periodic tasks
    asyncio.create_task(generate_random_metrics())
    
    yield
    
    # Clean up resources
    logger.info("Shutting down PostgreSQL metrics recorder")
    await metrics_recorder.shutdown()


app = FastAPI(lifespan=lifespan)


async def generate_random_metrics():
    """Background task to generate random metrics"""
    global metrics_recorder
    
    if not metrics_recorder:
        return
    
    while True:
        try:
            # Record a random gauge value
            await metrics_recorder.set_gauge(
                "custom_random_value",
                random.uniform(0, 100),
                {"category": random.choice(["cat_a", "cat_b", "cat_c"])}
            )
            
            # Record a counter increment
            await metrics_recorder.increment_counter(
                StandardMetrics.HTTP_REQUESTS_TOTAL.name,
                random.randint(1, 5),
                {"method": random.choice(["GET", "POST", "PUT", "DELETE"]),
                 "path": f"/api/resource/{random.randint(1, 10)}",
                 "status": str(random.choice([200, 201, 400, 404, 500]))}
            )
            
            # Record a histogram observation
            await metrics_recorder.observe_histogram(
                StandardMetrics.HTTP_REQUEST_DURATION_SECONDS.name,
                random.uniform(0.001, 2.0),
                {"endpoint": f"/api/endpoint/{random.randint(1, 5)}"}
            )
            
            # Sleep for a random interval
            await asyncio.sleep(random.uniform(0.5, 2.0))
        except Exception as e:
            logger.error(f"Error generating random metrics: {e}")
            await asyncio.sleep(5)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Middleware to record HTTP metrics"""
    global metrics_recorder
    
    if not metrics_recorder:
        return await call_next(request)
    
    start_time = time.time()
    
    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception as exc:
        status_code = 500
        await metrics_recorder.record_exception()
        raise exc
    finally:
        duration = time.time() - start_time
        
        # Record request duration
        await metrics_recorder.observe_histogram(
            StandardMetrics.HTTP_REQUEST_DURATION_SECONDS.name,
            duration,
            {"method": request.method, "path": request.url.path, "status": str(status_code)}
        )
        
        # Increment request counter
        await metrics_recorder.increment_counter(
            StandardMetrics.HTTP_REQUESTS_TOTAL.name,
            1,
            {"method": request.method, "path": request.url.path, "status": str(status_code)}
        )
    
    return response


@app.get("/", response_class=JSONResponse)
async def root():
    """Root endpoint"""
    return {"message": "PostgreSQL Metrics Example API", "endpoints": [
        "/metrics",
        "/metrics/aggregated",
        "/health",
        "/trigger_error"
    ]}


@app.get("/metrics", response_model=List[MetricResponse])
async def get_metrics(limit: int = 100, service: str = SERVICE_NAME):
    """Get raw metrics from PostgreSQL"""
    global metrics_recorder
    
    if not metrics_recorder:
        raise HTTPException(status_code=503, detail="Metrics recorder not initialized")
    
    try:
        async with metrics_recorder.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT 
                    metric_name, 
                    metric_type, 
                    metric_value, 
                    labels, 
                    timestamp 
                FROM metrics 
                WHERE service_name = $1
                ORDER BY timestamp DESC 
                LIMIT $2
                """,
                service, limit
            )
            
            return [
                MetricResponse(
                    metric_name=row["metric_name"],
                    metric_type=row["metric_type"],
                    metric_value=row["metric_value"],
                    labels=row["labels"],
                    timestamp=row["timestamp"].isoformat()
                )
                for row in rows
            ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching metrics: {str(e)}")


@app.get("/metrics/aggregated", response_model=List[AggregatedMetricResponse])
async def get_aggregated_metrics(
    window: int = 60,
    limit: int = 100,
    service: str = SERVICE_NAME
):
    """Get aggregated metrics from PostgreSQL"""
    global metrics_recorder
    
    if not metrics_recorder:
        raise HTTPException(status_code=503, detail="Metrics recorder not initialized")
    
    try:
        async with metrics_recorder.pool.acquire() as conn:
            # Trigger aggregation function for the specified window
            await conn.execute(
                "SELECT aggregate_metrics($1, $2)",
                window, service
            )
            
            # Fetch the aggregated metrics
            rows = await conn.fetch(
                """
                SELECT 
                    metric_name, 
                    metric_type, 
                    min_value,
                    max_value,
                    avg_value,
                    sum_value,
                    count_value,
                    labels, 
                    timestamp,
                    window_seconds
                FROM metrics_aggregated 
                WHERE service_name = $1
                AND window_seconds = $2
                ORDER BY timestamp DESC 
                LIMIT $3
                """,
                service, window, limit
            )
            
            return [
                AggregatedMetricResponse(
                    metric_name=row["metric_name"],
                    metric_type=row["metric_type"],
                    min_value=row["min_value"],
                    max_value=row["max_value"],
                    avg_value=row["avg_value"],
                    sum_value=row["sum_value"],
                    count_value=row["count_value"],
                    labels=row["labels"],
                    timestamp=row["timestamp"].isoformat(),
                    window_seconds=row["window_seconds"]
                )
                for row in rows
            ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching aggregated metrics: {str(e)}")


@app.get("/health", response_model=HealthCheckResponse)
async def health_check(
    recorder: PostgresMetricsRecorder = Depends(get_metrics_recorder)
):
    """
    Check the health of the metrics recorder.
    
    This endpoint returns health information about the PostgreSQL metrics recorder,
    including connection status, metrics counts, and configuration details.
    """
    is_healthy, details = await recorder.health_check()
    
    return {
        "healthy": is_healthy,
        "details": details
    }


@app.get("/trigger_error")
async def trigger_error():
    """Endpoint to trigger a deliberate error for testing"""
    error_id = str(uuid.uuid4())
    try:
        # Deliberately cause an exception
        raise ValueError(f"Deliberate test error with ID: {error_id}")
    except Exception as e:
        # Record the exception
        if metrics_recorder:
            await metrics_recorder.record_exception()
            await metrics_recorder.increment_counter(
                StandardMetrics.ERROR_COUNT.name,
                1,
                {"type": "ValueError", "endpoint": "/trigger_error"}
            )
        
        # Return the error details
        return {
            "error": "Deliberate test error triggered",
            "error_id": error_id,
            "message": str(e)
        }


async def get_metrics_recorder() -> PostgresMetricsRecorder:
    if metrics_recorder is None:
        raise HTTPException(status_code=503, detail="Metrics recorder not initialized")
    return metrics_recorder


@app.post("/query", response_model=List[MetricDataPoint])
async def query_metrics(
    query: QueryMetricsRequest,
    recorder: PostgresMetricsRecorder = Depends(get_metrics_recorder)
):
    """
    Query metrics from the PostgreSQL database.
    
    This endpoint allows querying metrics by name, time range, and labels.
    It also supports requesting aggregated metrics.
    """
    try:
        # Record query metric
        await recorder.increment_counter(
            "api_requests_total",
            1,
            {"method": "POST", "endpoint": "/query", "status": "200"}
        )
        
        # Query the metrics
        results = await recorder.query_metric(
            metric_name=query.metric_name,
            start_time=query.start_time,
            end_time=query.end_time,
            labels=query.labels,
            aggregation=query.aggregation
        )
        
        return results
    
    except Exception as e:
        # Record error metric
        await recorder.increment_counter(
            "api_requests_total",
            1,
            {"method": "POST", "endpoint": "/query", "status": "500"}
        )
        
        logger.error(f"Error querying metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metadata")
async def get_metadata(
    metric_name: Optional[str] = None,
    recorder: PostgresMetricsRecorder = Depends(get_metrics_recorder)
):
    """
    Get metadata for a specific metric or all metrics.
    
    Args:
        metric_name: Optional name of the metric to retrieve metadata for.
                    If not provided, metadata for all metrics is returned.
    """
    try:
        metadata = await recorder.get_metric_metadata(metric_name)
        
        # If it's a list, convert each item to dict
        if isinstance(metadata, list):
            return [m.dict() for m in metadata]
        
        # Otherwise, return the single metadata object as dict
        return metadata.dict()
    
    except Exception as e:
        logger.error(f"Error getting metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/simulate_load")
async def simulate_load(
    duration: int = Query(60, description="Duration of load simulation in seconds"),
    recorder: PostgresMetricsRecorder = Depends(get_metrics_recorder)
):
    """
    Simulate load by generating random metrics.
    
    This endpoint runs a background task that simulates application load
    by generating random metrics for a specified duration.
    """
    # Start a background task to simulate load
    asyncio.create_task(
        _simulate_load_task(duration, recorder)
    )
    
    return {
        "message": f"Load simulation started for {duration} seconds",
        "status": "running"
    }


async def _simulate_load_task(duration: int, recorder: PostgresMetricsRecorder):
    """
    Background task that simulates application load.
    
    Args:
        duration: Duration of the simulation in seconds
        recorder: The metrics recorder instance
    """
    logger.info(f"Starting load simulation for {duration} seconds")
    
    regions = ["us-east", "us-west", "eu-central", "ap-southeast"]
    endpoints = ["/api/users", "/api/products", "/api/orders", "/api/payments"]
    methods = ["GET", "POST", "PUT", "DELETE"]
    statuses = ["200", "201", "400", "404", "500"]
    
    end_time = time.time() + duration
    
    while time.time() < end_time:
        # Simulate user activity
        for region in regions:
            # Update active users gauge with random values
            await recorder.set_gauge(
                "active_users",
                random.randint(50, 500),
                {"region": region}
            )
        
        # Simulate API requests
        for _ in range(random.randint(5, 20)):
            method = random.choice(methods)
            endpoint = random.choice(endpoints)
            status = random.choice(statuses)
            
            # Record request counter
            await recorder.increment_counter(
                "api_requests_total",
                1,
                {"method": method, "endpoint": endpoint, "status": status}
            )
            
            # Record request duration
            await recorder.observe_histogram(
                "request_duration_seconds",
                random.uniform(0.01, 2.0),
                {"method": method, "endpoint": endpoint}
            )
        
        # Wait a short time before generating more metrics
        await asyncio.sleep(0.1)
    
    logger.info("Load simulation completed")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("postgres_metrics_example:app", host="0.0.0.0", port=8000, reload=True) 