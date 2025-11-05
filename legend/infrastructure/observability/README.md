# IDP 可观测性框架

IDP可观测性框架提供了统一的指标记录、分布式追踪和错误监控能力，支持多种后端实现，包括内存存储、Prometheus、Sentry及PostgreSQL持久化。

## 核心功能

- **指标监控**：记录计数器、直方图和量规指标，支持标签和元数据
- **分布式追踪**：记录请求的完整调用链，包括跨服务调用
- **错误监控**：集成错误捕获和上报机制
- **PostgreSQL持久化**：支持将指标和追踪数据持久化到PostgreSQL数据库

## 快速开始

### 基本配置

```python
from idp.framework.infrastructure.observability import create_observability, ObservabilityConfig

# 创建可观测性配置
config = ObservabilityConfig(
    service_name="my-service",
    metrics=MetricsConfig(enabled=True, name_prefix="my_app"),
    tracing=TracingConfig(enabled=True, sample_rate=0.1)
)

# 初始化可观测性组件
observability = create_observability(config)

# 在应用启动时初始化
@app.on_event("startup")
async def startup():
    await observability.initialize()

# 在应用关闭时清理资源
@app.on_event("shutdown")
async def shutdown():
    await observability.cleanup()
```

### 使用PostgreSQL持久化

#### 1. 统一配置方式

```python
from idp.framework.infrastructure.observability import (
    create_observability, ObservabilityConfig, PostgresObservabilityConfig
)

# 创建带PostgreSQL持久化的配置
config = ObservabilityConfig(
    service_name="my-service",
    metrics=MetricsConfig(enabled=True, name_prefix="my_app"),
    tracing=TracingConfig(enabled=True, sample_rate=0.1),
    postgres=PostgresObservabilityConfig(
        enabled=True,
        common=PostgresCommonConfig(
            connection="postgresql://user:pass@localhost:5432/observability",
            schema="observability",
            retention_days=30,
            batch_size=100
        ),
        metrics_table="app_metrics",
        metrics_metadata_table="app_metric_metadata",
        spans_table="app_spans",
        span_events_table="app_span_events",
        flush_interval=5.0
    )
)

# 初始化可观测性组件
observability = create_observability(config)
```

#### 2. 单独配置方式

```python
from idp.framework.infrastructure.observability import create_observability, ObservabilityConfig

# 创建带PostgreSQL持久化的配置
config = ObservabilityConfig(
    service_name="my-service",
    metrics=MetricsConfig(
        enabled=True,
        name_prefix="my_app",
        recorder_type="POSTGRES",
        postgres_connection="postgresql://user:pass@localhost:5432/observability",
        postgres_schema="observability",
        postgres_metrics_table="app_metrics",
        postgres_metadata_table="app_metric_metadata",
        postgres_retention_days=30
    ),
    tracing=TracingConfig(
        enabled=True,
        sample_rate=0.1,
        tracer_type="POSTGRES",
        postgres_connection="postgresql://user:pass@localhost:5432/observability",
        postgres_schema="observability",
        postgres_spans_table="app_spans",
        postgres_events_table="app_span_events",
        postgres_retention_days=30,
        postgres_flush_interval=5.0
    )
)

# 初始化可观测性组件
observability = create_observability(config)
```

### 从YAML配置文件加载

```python
from idp.framework.infrastructure.observability import create_observability_from_config

# 从配置文件加载
observability = await create_observability_from_config("config/observability.yml", "default")

# 或使用环境变量指定配置文件和环境
# export OBSERVABILITY_CONFIG_FILE=config/observability.yml
# export OBSERVABILITY_ENV=production
observability = await create_observability_from_config()
```

## PostgreSQL表结构

PostgreSQL持久化功能需要以下表结构：

```sql
-- 指标元数据表
CREATE TABLE observability.observability_metric_metadata (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    unit VARCHAR(50),
    type VARCHAR(20) NOT NULL,
    label_keys JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name)
);

-- 指标数据表
CREATE TABLE observability.observability_metrics (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    labels JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 追踪Span表
CREATE TABLE observability.observability_spans (
    trace_id VARCHAR(32) NOT NULL,
    span_id VARCHAR(16) NOT NULL,
    parent_span_id VARCHAR(16),
    name VARCHAR(255) NOT NULL,
    kind VARCHAR(20) NOT NULL,
    start_time BIGINT NOT NULL,
    end_time BIGINT,
    duration BIGINT,
    status VARCHAR(20),
    status_message TEXT,
    attributes JSONB,
    service_name VARCHAR(100) NOT NULL,
    resource_attributes JSONB,
    PRIMARY KEY (trace_id, span_id)
);

-- Span事件表
CREATE TABLE observability.observability_span_events (
    id SERIAL PRIMARY KEY,
    trace_id VARCHAR(32) NOT NULL,
    span_id VARCHAR(16) NOT NULL,
    name VARCHAR(255) NOT NULL,
    timestamp BIGINT NOT NULL,
    attributes JSONB,
    FOREIGN KEY (trace_id, span_id) REFERENCES observability.observability_spans(trace_id, span_id)
);

-- 为常用查询添加索引
CREATE INDEX idx_metrics_name_timestamp ON observability.observability_metrics(name, timestamp);
CREATE INDEX idx_metrics_labels ON observability.observability_metrics USING GIN(labels);
CREATE INDEX idx_spans_trace_id ON observability.observability_spans(trace_id);
CREATE INDEX idx_spans_service_name ON observability.observability_spans(service_name);
CREATE INDEX idx_spans_start_time ON observability.observability_spans(start_time);
```

## 性能优化建议

1. **批量写入**：调整`batch_size`参数以优化写入性能，一般建议：
   - 低流量应用: 50-100
   - 中等流量: 100-500 
   - 高流量: 500-1000

2. **刷新间隔**：调整`flush_interval`参数平衡实时性和性能，一般建议：
   - 对实时性要求高: 1-5秒
   - 一般场景: 5-15秒
   - 批处理场景: 15-60秒

3. **数据清理**：设置合理的`retention_days`以防止数据量过大：
   - 短期数据: 7-14天
   - 中期数据: 30-90天
   - 长期数据: 根据业务需求定制

4. **连接池设置**：对于高流量应用，确保PostgreSQL连接池配置合理：
   - 最小连接数: 5-10
   - 最大连接数: 根据服务器性能和并发需求设置

## 查询示例

### 指标查询

```sql
-- 查询指定时间范围内的指标
SELECT 
    name, 
    AVG(value) as avg_value, 
    MAX(value) as max_value, 
    MIN(value) as min_value, 
    COUNT(*) as sample_count
FROM 
    observability.observability_metrics
WHERE 
    name LIKE 'app_%' AND
    timestamp BETWEEN NOW() - INTERVAL '1 hour' AND NOW()
GROUP BY 
    name
ORDER BY 
    avg_value DESC;

-- 带标签过滤的查询
SELECT 
    timestamp, 
    value
FROM 
    observability.observability_metrics
WHERE 
    name = 'app_http_request_duration' AND
    labels->>'method' = 'GET' AND
    labels->>'path' = '/api/users'
ORDER BY 
    timestamp DESC
LIMIT 100;
```

### 追踪查询

```sql
-- 查询慢请求
SELECT 
    trace_id, 
    name, 
    service_name, 
    start_time, 
    duration / 1000000.0 as duration_ms
FROM 
    observability.observability_spans
WHERE 
    kind = 'SERVER' AND
    start_time > extract(epoch from now() - interval '1 hour') * 1000000000
ORDER BY 
    duration DESC
LIMIT 20;

-- 查询特定trace的所有span
SELECT 
    s.span_id, 
    s.parent_span_id, 
    s.name, 
    s.service_name, 
    s.duration / 1000000.0 as duration_ms,
    s.attributes
FROM 
    observability.observability_spans s
WHERE 
    s.trace_id = '1234567890abcdef1234567890abcdef'
ORDER BY 
    s.start_time;
```

## 更多资源

- [设计文档](./Design.md)
- [配置示例](../../config/observability.postgres-example.yml)
- [API参考文档](./API.md)
- [PostgreSQL示例](./examples/postgres_example.py) 