# Metrics Recorders for Observability Framework

This package provides various metrics recorders for the IDP observability framework. These recorders implement the `IMetricsRecorder` interface defined in the core module and provide specialized functionality for recording and querying metrics in different backends.

## Available Recorders

- **BaseMetricsRecorder**: A base implementation that provides common functionality for all metrics recorders.
- **MemoryMetricsRecorder**: A simple in-memory metrics recorder suitable for development and testing.
- **PrometheusMetricsRecorder**: A recorder that exports metrics to Prometheus.
- **PostgresMetricsRecorder**: A recorder that stores metrics in a PostgreSQL database.

## PostgreSQL Metrics Recorder

The PostgreSQL metrics recorder provides the ability to store and query metrics in a PostgreSQL database. This is particularly useful for:

- Long-term storage of metrics data
- Complex queries and analytics on historical metrics
- Generating custom reports and dashboards
- Integration with existing data analytics pipelines

### Setup

1. **Database Prerequisites**:
   - PostgreSQL 12+ installed and configured
   - A dedicated database for metrics storage (recommended)
   - A user with appropriate privileges

2. **Configuration**:
   ```python
   from idp.framework.infrastructure.observability.metrics.postgres import PostgresMetricsConfig, PostgresMetricsRecorder
   
   # Configure the recorder
   postgres_config = PostgresMetricsConfig(
       dsn="postgresql://username:password@localhost:5432/metrics_db",
       batch_size=50,
       flush_interval=5.0,
       retention_days=30,
       aggregation_interval=3600,  # 1 hour
       max_pool_size=10,
       min_pool_size=2
   )
   
   # Initialize the recorder
   metrics_recorder = PostgresMetricsRecorder(
       service_name="my-service",
       config=postgres_config,
       prefix="app_"  # Optional prefix for all metrics
   )
   
   # Initialize the recorder (creates tables if they don't exist)
   await metrics_recorder.initialize()
   ```

3. **Schema Initialization**:
   The recorder will automatically create the required tables during initialization:
   - `metrics_metadata`: Stores metadata about registered metrics
   - `metrics_values`: Stores recorded metric values with timestamps and labels
   - `metrics_aggregates`: Stores aggregated metrics data

### Usage

1. **Register Metrics**:
   ```python
   from idp.framework.infrastructure.observability.core.metadata import MetricMetadata, MetricType
   
   # Register a counter
   await metrics_recorder.register_metric(
       MetricMetadata(
           name="api_requests_total",
           type=MetricType.COUNTER,
           help="Total number of API requests",
           unit="requests",
           label_names=["endpoint", "method", "status"]
       )
   )
   
   # Register a histogram
   await metrics_recorder.register_metric(
       MetricMetadata(
           name="api_request_duration_seconds",
           type=MetricType.HISTOGRAM,
           help="API request duration in seconds",
           unit="seconds",
           label_names=["endpoint", "method"],
           buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
       )
   )
   ```

2. **Record Metrics**:
   ```python
   # Increment a counter
   await metrics_recorder.increment_counter(
       "api_requests_total",
       1,
       {"endpoint": "/api/users", "method": "GET", "status": "200"}
   )
   
   # Record a histogram observation
   await metrics_recorder.observe_histogram(
       "api_request_duration_seconds",
       0.123,  # Value in seconds
       {"endpoint": "/api/users", "method": "GET"}
   )
   
   # Set a gauge value
   await metrics_recorder.set_gauge(
       "active_users",
       42,
       {}  # No labels
   )
   ```

3. **Query Metrics**:
   ```python
   from datetime import datetime, timedelta
   
   # Query metrics data
   results = await metrics_recorder.query_metric(
       metric_name="api_requests_total",
       start_time=datetime.now() - timedelta(hours=24),
       end_time=datetime.now(),
       labels={"endpoint": "/api/users", "method": "GET"},
       aggregation="sum"  # Options: sum, count, min, max, avg
   )
   
   # Get metadata about registered metrics
   metadata = await metrics_recorder.get_metric_metadata("api_requests_total")
   ```

4. **Lifecycle Management**:
   ```python
   # In FastAPI applications:
   @app.on_event("startup")
   async def startup_event():
       await metrics_recorder.initialize()
       
   @app.on_event("shutdown")
   async def shutdown_event():
       await metrics_recorder.shutdown()
   ```

### Performance Considerations

The PostgreSQL metrics recorder includes several features for optimal performance:

1. **Connection Pooling**: Uses a connection pool to efficiently manage database connections
2. **Batch Processing**: Accumulates metrics in memory and flushes them in batches
3. **Automatic Cleanup**: Periodically removes old metrics data based on retention policy
4. **Aggregation**: Automatically aggregates high-cardinality data to reduce storage requirements
5. **Health Checks**: Provides health check methods to monitor the recorder's status

### See Also

- See `postgres_metrics_example.py` in the examples directory for a complete FastAPI application example.
- Refer to the API documentation for detailed information about all available methods and configuration options. 