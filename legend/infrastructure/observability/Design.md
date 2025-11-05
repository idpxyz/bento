# Observability 子系统设计文档

## 执行摘要

本文档详细描述了 DDD Framework Infrastructure 层中 Observability 子系统的设计方案。该系统旨在提供:
- 统一的可观测性抽象层
- 全面的监控指标采集
- 分布式追踪能力
- 灵活的多后端支持
- 低侵入性的集成方案

## 文档信息

| 版本  | 日期       | 作者 | 变更说明    | 评审状态 |
|------|------------|------|------------|----------|
| v1.0 | 2024-03-XX | -    | 初始版本    | 待评审   |

---

## 一、系统概述

- **定位**：Observability（可观测性）为典型的横切关注点，提供指标采集、日志统计、错误追踪和链路追踪功能。  
- **边界**：属于 DDD Framework 的 Infrastructure 层，不直接依赖 Domain/Application 业务，只向上暴露抽象接口供用例级或框架级调用。  
- **目标**：实现低侵入、高一致、易扩展的观测方案，支持多种后端（Prometheus、Sentry、OTel、Datadog）。

## 二、模块划分与组件职责

### 2.1 目录结构

```
infrastructure/observability/
├─ core/
│   ├─ interfaces.py      # 核心抽象接口定义
│   └─ constants.py       # 常量与默认配置
├─ metrics/
│   ├─ recorder.py        # 指标记录抽象基类
│   ├─ prometheus.py      # Prometheus 实现
│   ├─ memory.py          # 内存实现（用于测试和开发环境）
│   └─ datadog.py        # Datadog 实现
├─ tracing/
│   ├─ tracer.py         # 链路追踪抽象
│   ├─ opentelemetry.py  # OpenTelemetry 实现
│   └─ sentry.py         # Sentry APM 实现
├─ middleware/           
│   ├─ request_id.py     # 请求唯一 ID
│   ├─ metrics.py        # 请求指标收集
│   └─ tracing.py        # 分布式追踪注入
└─ listeners/            
    ├─ sqlalchemy.py     # 数据库操作监听
    ├─ cache.py          # 缓存操作监听
    └─ messaging.py      # 消息中间件监听
```

### 2.2 核心接口定义

```python
# core/interfaces.py

class IMetricsRecorder(Protocol):
    """指标记录器接口"""
    async def increment_counter(
        self, 
        name: str, 
        value: float = 1.0, 
        labels: dict[str, str] | None = None
    ) -> None: ...
    
    async def observe_histogram(
        self, 
        name: str, 
        value: float, 
        labels: dict[str, str] | None = None
    ) -> None: ...
    
    async def set_gauge(
        self, 
        name: str, 
        value: float, 
        labels: dict[str, str] | None = None
    ) -> None: ...

class ITracer(Protocol):
    """链路追踪接口"""
    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: dict[str, str] | None = None
    ) -> AsyncContextManager[Span]: ...
    
    def inject_context(
        self,
        carrier: dict[str, str]
    ) -> None: ...
```

### 2.3 配置定义

```python
# core/config.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict

class MetricsConfig(BaseModel):
    """指标采集配置"""
    enabled: bool = Field(default=True, description="是否启用指标采集")
    prometheus_port: int = Field(default=9090, description="Prometheus 指标暴露端口")
    prefix: str = Field(default="app", description="指标名称前缀")
    default_labels: Dict[str, str] = Field(
        default_factory=dict,
        description="默认标签集"
    )
    buckets: Dict[str, List[float]] = Field(
        default_factory=lambda: {
            "http_request_duration_seconds": [0.01, 0.05, 0.1, 0.5, 1.0],
            "db_operation_duration_seconds": [0.001, 0.005, 0.01, 0.05, 0.1]
        },
        description="直方图 bucket 定义"
    )
    # 新增: 基础的聚合规则配置
    aggregation_interval: int = Field(
        default=60,
        description="指标聚合间隔(秒)"
    )

class TracingConfig(BaseModel):
    """链路追踪配置"""
    enabled: bool = Field(default=True, description="是否启用链路追踪")
    service_name: str = Field(..., description="服务名称")
    sample_rate: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="采样率"
    )
    otel_endpoint: Optional[str] = Field(
        default=None, 
        description="OpenTelemetry Collector 地址"
    )
    sentry_dsn: Optional[str] = Field(
        default=None,
        description="Sentry DSN"
    )
    ignored_paths: List[str] = Field(
        default_factory=lambda: ["/metrics", "/health"],
        description="不进行追踪的路径"
    )

class ObservabilityConfig(BaseModel):
    """可观测性总配置"""
    env: str = Field(default="dev", description="环境标识")
    metrics: MetricsConfig = Field(default_factory=MetricsConfig)
    tracing: TracingConfig
    request_timeout: float = Field(
        default=30.0,
        description="监控数据上报超时时间"
    )
    batch_size: int = Field(
        default=100,
        description="批量上报大小"
    )
    flush_interval: float = Field(
        default=15.0,
        description="强制刷新间隔(秒)"
    )
```

配置加载示例:

```python
# 从环境变量加载
config = ObservabilityConfig(
    env=os.getenv("APP_ENV", "dev"),
    tracing=TracingConfig(
        service_name="user-service",
        otel_endpoint=os.getenv("OTEL_ENDPOINT"),
        sentry_dsn=os.getenv("SENTRY_DSN")
    )
)

# 从配置文件加载
config = ObservabilityConfig.parse_file("observability.yaml")
```

### 2.4 度量项元信息模型

```python
# core/metadata.py
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class MetricType(str, Enum):
    """度量项类型"""
    COUNTER = "counter"      # 计数器
    GAUGE = "gauge"         # 仪表盘
    HISTOGRAM = "histogram" # 直方图
    SUMMARY = "summary"     # 摘要

class MetricMetadata(BaseModel):
    """度量项元信息"""
    name: str = Field(..., description="指标名称")
    type: MetricType = Field(..., description="指标类型")
    help: str = Field(..., description="指标描述")
    unit: str = Field(default="", description="单位(如 seconds, bytes)")
    label_names: List[str] = Field(default_factory=list, description="标签名列表")
    buckets: Optional[List[float]] = Field(
        default=None, 
        description="直方图 bucket 列表(仅 histogram 类型)"
    )
    objectives: Optional[Dict[float, float]] = Field(
        default=None,
        description="分位数目标(仅 summary 类型)"
    )
    # 新增: 基础的告警阈值定义
    alert_threshold: Optional[float] = Field(
        default=None,
        description="告警阈值"
    )

class StandardMetrics:
    """标准度量项定义"""
    
    # 系统自监控指标
    METRICS_PROCESSING_DURATION = MetricMetadata(
        name="obs_metrics_processing_seconds",
        type=MetricType.HISTOGRAM,
        help="Metrics processing duration",
        unit="seconds",
        buckets=[0.001, 0.005, 0.01, 0.05, 0.1],
        alert_threshold=1.0  # 处理时间超过1秒告警
    )
    
    DROPPED_METRICS = MetricMetadata(
        name="obs_dropped_metrics_total",
        type=MetricType.COUNTER,
        help="Number of dropped metrics",
        alert_threshold=100  # 丢弃超过100个指标告警
    )
    
    # HTTP 相关
    HTTP_REQUEST_TOTAL = MetricMetadata(
        name="http_requests_total",
        type=MetricType.COUNTER,
        help="Total number of HTTP requests",
        label_names=["method", "path", "status"]
    )
    
    HTTP_REQUEST_DURATION = MetricMetadata(
        name="http_request_duration_seconds",
        type=MetricType.HISTOGRAM,
        help="HTTP request duration in seconds",
        unit="seconds",
        label_names=["method", "path"],
        buckets=[0.01, 0.05, 0.1, 0.5, 1.0]
    )
    
    # 数据库相关
    DB_CONNECTIONS = MetricMetadata(
        name="db_connections",
        type=MetricType.GAUGE,
        help="Number of database connections",
        label_names=["pool_name", "state"]
    )
    
    DB_OPERATION_DURATION = MetricMetadata(
        name="db_operation_duration_seconds",
        type=MetricType.HISTOGRAM,
        help="Database operation duration in seconds",
        unit="seconds",
        label_names=["operation", "table"],
        buckets=[0.001, 0.005, 0.01, 0.05, 0.1]
    )
    
    # 缓存相关
    CACHE_HITS = MetricMetadata(
        name="cache_hits_total",
        type=MetricType.COUNTER,
        help="Total number of cache hits",
        label_names=["cache_name"]
    )
    
    # 消息队列相关
    MESSAGE_PROCESSED = MetricMetadata(
        name="message_processed_total",
        type=MetricType.COUNTER,
        help="Total number of processed messages",
        label_names=["topic", "consumer_group"]
    )

    @classmethod
    def get_all_metrics(cls) -> List[MetricMetadata]:
        """获取所有标准度量项"""
        return [
            value for name, value in vars(cls).items()
            if isinstance(value, MetricMetadata)
        ]
```

使用示例:

```python
# 在指标记录器实现中使用元信息
class PrometheusRecorder(IMetricsRecorder):
    def __init__(self):
        self._metrics = {}
        # 预注册所有标准度量项
        for metric in StandardMetrics.get_all_metrics():
            self._register_metric(metric)
    
    def _register_metric(self, metadata: MetricMetadata):
        if metadata.type == MetricType.COUNTER:
            self._metrics[metadata.name] = Counter(
                metadata.name,
                metadata.help,
                metadata.label_names
            )
        elif metadata.type == MetricType.HISTOGRAM:
            self._metrics[metadata.name] = Histogram(
                metadata.name,
                metadata.help,
                metadata.label_names,
                buckets=metadata.buckets
            )
        # ... 其他类型处理
```

### 2.5 与日志系统的集成

本子系统不实现日志功能，而是通过以下方式与独立的日志系统集成：

1. **指标导出**
   - 重要的监控指标变化会通过结构化日志记录
   - 异常监控事件会触发日志记录

2. **追踪关联**
   - 在日志中注入 trace_id 和 span_id
   - 支持从日志直接跳转到对应的追踪详情

3. **上下文共享**
   - 共享请求上下文（request_id, user_id 等）
   - 保持日志与追踪的标签一致性

### 2.3 标准指标集

#### HTTP 层面
- `http_requests_total{method, path, status}`：请求总数
- `http_request_duration_seconds{method, path}`：请求延迟分布
- `http_request_size_bytes{method, path}`：请求大小分布
- `http_response_size_bytes{method, path}`：响应大小分布

#### 数据库层面
- `db_connections{pool_name, state}`：连接池状态
- `db_operation_duration_seconds{operation, table}`：操作延迟
- `db_errors_total{operation, error_type}`：错误计数

#### 缓存层面
- `cache_hits_total{cache_name}`：缓存命中计数
- `cache_misses_total{cache_name}`：缓存未命中计数
- `cache_operation_duration_seconds{operation}`：操作延迟

#### 消息队列层面
- `message_published_total{topic}`：消息发布计数
- `message_consumed_total{topic, consumer_group}`：消息消费计数
- `message_processing_duration_seconds{topic}`：处理延迟

### 2.6 指标记录器实现

#### 2.6.1 基础记录器

`BaseMetricsRecorder` 实现了 `IMetricsRecorder` 接口的通用逻辑：
- 指标缓存管理
- 批量刷新机制
- 处理时间测量
- 健康检查支持

#### 2.6.2 Prometheus 记录器

`PrometheusRecorder` 基于 Prometheus 客户端库实现：
- 支持直接暴露 HTTP 端点
- 支持推送到 PushGateway
- 支持自定义直方图 buckets
- 完整的标签管理

#### 2.6.3 内存记录器

`MemoryMetricsRecorder` 将指标存储在内存中，主要用于测试和开发环境：
- 轻量级实现，无外部依赖
- 支持所有指标类型
- 提供额外的查询方法
- 可用于单元测试和快速开发

内存记录器示例：

```python
# 创建内存指标记录器实例
recorder = MemoryMetricsRecorder(
    prefix="app",
    default_labels={"service": "api", "environment": "dev"}
)

# 记录指标
await recorder.increment_counter("http_requests_total", labels={"method": "GET"})
await recorder.observe_histogram("http_request_duration_seconds", 0.45)

# 获取记录的指标
counter_value = recorder.get_counter_value("http_requests_total", {"method": "GET"})
histogram_values = recorder.get_histogram_values("http_request_duration_seconds")

# 用于测试的清理方法
recorder.clear()
```

#### 2.6.4 工厂模式

通过 `MetricsRecorderFactory` 创建不同类型的指标记录器：

```python
# 从配置创建
recorder = MetricsRecorderFactory.create_from_config(config.metrics)

# 直接指定类型
recorder = MetricsRecorderFactory.create(
    recorder_type="MEMORY",  # 或 MetricsRecorderType.MEMORY
    prefix="app",
    default_labels={"service": "user-service"}
)
```

## 三、数据流转路径

### 3.1 请求处理流程

1. **入口层**
   - FastAPI 中间件链处理顺序：
     1. RequestID 生成与注入
     2. 认证信息解析
     3. 追踪上下文提取
     4. 指标记录准备

2. **业务层**
   - 服务方法装饰器自动：
     1. 创建子 Span
     2. 记录方法执行时间
     3. 捕获并分类异常

3. **数据访问层**
   - ORM/缓存操作自动：
     1. 记录操作类型与目标
     2. 测量执行时间
     3. 统计错误率

4. **出口层**
   - 响应处理：
     1. 计算总处理时间
     2. 更新请求计数器
     3. 注入追踪信息

### 3.2 异常处理流程

1. **捕获阶段**
   - 记录异常类型与堆栈
   - 关联当前请求上下文
   - 生成错误 ID

2. **分类阶段**
   - 区分业务异常与系统异常
   - 确定错误等级
   - 选择处理策略

3. **处理阶段**
   - 错误信息标准化
   - 触发告警（可选）
   - 记录详细日志

4. **恢复阶段**
   - 执行补偿操作
   - 更新错误计数
   - 清理上下文

## 四、关键设计权衡

| 关注点           | 方案                                                         | 权衡                                                                                 |
|------------------|--------------------------------------------------------------|--------------------------------------------------------------------------------------|
| **侵入性**       | 仅在中间件和基础设施层依赖抽象接口，业务层最低耦合               | 增加了一个基础设施子包和 DI 配置，但避免了业务代码直接依赖第三方 SDK                  |
| **一致性**       | 全链路同一套标签（service/env/module/user_id/tenant_id/request_id） | 标签设计需平衡维度丰富性与 TSDB 基数控制                                           |
| **性能开销**     | 异步/批量/采样上报；本地内存注册 Vector；轻量钩子                 | 需要在高 QPS 场景调整采样率，避免监控系统成为瓶颈                                    |
| **可扩展性**     | 抽象接口＋DI 容器，新增后端仅需实现接口                          | 多后端实现增加维护成本，但通过接口规范化可有效隔离差异                              |
| **可测试性**     | Mock 实现接口用于单元测试                                       | 需要构造测试替身，但可以简化测试编写                                                |

## 五、非功能性要求

### 5.1 可靠性保证
- 本地指标缓存，避免网络抖动影响
- 异步批量上报，降低系统负载
- 关键组件健康检查
- 基于阈值的简单告警
- 优雅降级机制

### 5.2 性能优化
- 采用无锁数据结构
- 内存队列缓冲
- 批量处理机制
- 采样率动态调整
- 异步处理管道

### 5.3 安全措施
- 指标访问认证
- 敏感数据脱敏
- 访问频率限制
- 白名单机制

### 5.4 运维支持
- 配置热更新
- 监控自监控
- 诊断接口
- 容量预估

## 六、最佳实践建议

### 6.1 指标设计
- 遵循 RED 方法论（Rate、Error、Duration）
- 避免高基数标签
- 合理设置 Bucket 区间
- 规范命名约定

### 6.2 追踪配置
- 根据场景调整采样率
- 合理设置 Span 属性
- 注意追踪上下文传递
- 控制 Span 事件数量

### 6.3 与日志的协同
- 确保 trace_id 在日志中的一致性
- 适当的日志关联采样策略
- 合理使用结构化字段
- 注意性能影响

## 七、演进路线

### 7.1 近期计划
1. 完善 Prometheus 集成
2. 添加 OpenTelemetry 支持
3. 实现日志结构化
4. 优化性能开销

### 7.2 中期目标
1. 支持更多监控后端
2. 增强告警能力
3. 提供监控面板模板
4. 完善运维工具

### 7.3 长期展望
1. 智能异常检测
2. 自适应采样
3. 自动化运维
4. 多集群支持

## 八、总结

本设计方案通过:
- 清晰的层次划分
- 标准化的接口定义
- 完善的功能覆盖
- 合理的性能权衡
- 可扩展的架构设计

为构建企业级可观测性系统提供了完整的技术框架。后续将根据实际运行反馈持续优化和演进。

## 九、数据持久化方案

### 9.1 PostgreSQL持久化实现

除了支持各种专业的可观测性后端（如Prometheus、Sentry等）外，本子系统还提供了将指标和追踪数据持久化到PostgreSQL数据库的能力。这种方式特别适合以下场景：

1. **长期数据存储** - 保留历史数据用于趋势分析和审计
2. **自定义查询分析** - 利用SQL查询能力进行高级分析
3. **低依赖部署** - 在不引入专业监控工具的情况下实现可观测性
4. **统一存储** - 将指标和追踪数据存储在同一个数据库中简化管理

#### 9.1.1 数据模型设计

**指标数据表结构**:

```sql
-- 指标元数据表
CREATE TABLE observability_metric_metadata (
    name VARCHAR(255) PRIMARY KEY,            -- 指标名称
    type VARCHAR(50) NOT NULL,                -- 指标类型(counter/gauge/histogram/summary)
    help TEXT,                                -- 指标说明
    unit VARCHAR(50),                         -- 单位(如 seconds, bytes)
    label_names JSONB,                        -- 标签名列表
    buckets JSONB,                            -- 直方图bucket列表
    objectives JSONB,                         -- 分位数目标
    alert_threshold FLOAT,                    -- 告警阈值
    created_at TIMESTAMP WITH TIME ZONE       -- 创建时间
);

-- 指标数据表
CREATE TABLE observability_metrics (
    id SERIAL PRIMARY KEY,                    -- 主键
    name VARCHAR(255) NOT NULL,               -- 指标名称
    type VARCHAR(50) NOT NULL,                -- 指标类型
    value FLOAT NOT NULL,                     -- 指标值
    labels JSONB,                             -- 标签集(JSON格式)
    timestamp TIMESTAMP WITH TIME ZONE,       -- 记录时间
    INDEX idx_metrics_name_timestamp (name, timestamp)  -- 索引
);
```

**追踪数据表结构**:

```sql
-- Span数据表
CREATE TABLE observability_spans (
    id SERIAL PRIMARY KEY,                    -- 主键
    trace_id VARCHAR(36) NOT NULL,            -- 追踪ID
    span_id VARCHAR(36) NOT NULL,             -- SpanID
    parent_span_id VARCHAR(36),               -- 父SpanID
    name VARCHAR(255) NOT NULL,               -- Span名称
    kind VARCHAR(50) NOT NULL,                -- Span类型
    service_name VARCHAR(100) NOT NULL,       -- 服务名称
    start_time DOUBLE PRECISION NOT NULL,     -- 开始时间
    end_time DOUBLE PRECISION,                -- 结束时间
    duration DOUBLE PRECISION,                -- 持续时间
    status VARCHAR(50) NOT NULL,              -- 状态(OK/ERROR)
    status_message TEXT,                      -- 状态消息
    attributes JSONB,                         -- 属性集(JSON格式)
    timestamp TIMESTAMP WITH TIME ZONE,       -- 记录时间
    UNIQUE (trace_id, span_id),               -- 唯一约束
    INDEX idx_spans_trace_id (trace_id),      -- 索引
    INDEX idx_spans_timestamp (timestamp)     -- 索引
);

-- Span事件表
CREATE TABLE observability_span_events (
    id SERIAL PRIMARY KEY,                    -- 主键
    trace_id VARCHAR(36) NOT NULL,            -- 追踪ID
    span_id VARCHAR(36) NOT NULL,             -- SpanID
    name VARCHAR(255) NOT NULL,               -- 事件名称
    timestamp DOUBLE PRECISION NOT NULL,      -- 事件发生时间
    attributes JSONB,                         -- 属性集(JSON格式)
    created_at TIMESTAMP WITH TIME ZONE,      -- 记录时间
    INDEX idx_span_events_span_id (span_id),  -- 索引
    INDEX idx_span_events_trace_id (trace_id) -- 索引
);
```

#### 9.1.2 关键特性

1. **批量写入** - 使用批处理方式提高写入性能
2. **异步处理** - 非阻塞的异步写入避免影响应用性能
3. **自动清理** - 根据保留策略自动清理过期数据
4. **历史查询** - 提供丰富的查询API访问历史数据
5. **连接池管理** - 高效管理数据库连接
6. **错误恢复** - 连接错误重试和数据缓冲机制

#### 9.1.3 配置方式

可以通过两种方式配置PostgreSQL持久化:

**1. 单独配置**

```python
# 指标配置
metrics_recorder = MetricsRecorderFactory.create(
    recorder_type=MetricsRecorderType.POSTGRES,
    connection_string="postgresql://user:pass@localhost:5432/db",
    prefix="app",
    schema_name="observability",
    table_name="app_metrics", 
    metadata_table_name="app_metric_metadata",
    retention_days=90
)

# 追踪配置
tracer = TracerFactory.create(
    tracer_type=TracerType.POSTGRES,
    service_name="api-service",
    connection_string="postgresql://user:pass@localhost:5432/db",
    schema_name="observability",
    spans_table_name="app_spans",
    events_table_name="app_span_events",
    retention_days=90
)
```

**2. 通过统一配置**

```python
# 创建统一配置
config = ObservabilityConfig(
    env="production",
    metrics=MetricsConfig(enabled=True),
    tracing=TracingConfig(
        service_name="api-service",
        enabled=True
    ),
    postgres=PostgresObservabilityConfig(
        enabled=True,
        common=PostgresCommonConfig(
            connection="postgresql://user:pass@localhost:5432/db",
            schema="observability",
            retention_days=90,
            batch_size=100
        ),
        metrics_table="app_metrics",
        metrics_metadata_table="app_metric_metadata",
        spans_table="app_spans",
        span_events_table="app_span_events",
        flush_interval=5.0
    )
)

# 使用配置创建实例
metrics_recorder = MetricsRecorderFactory.create_from_config(config.metrics)
tracer = TracerFactory.create_from_config(config.tracing)
```

或者可以通过环境变量配置:

```
# PostgreSQL配置
export POSTGRES_ENABLED=true
export POSTGRES_CONNECTION="postgresql://user:pass@localhost:5432/db"
export POSTGRES_SCHEMA="observability"
export POSTGRES_RETENTION_DAYS=90
export POSTGRES_BATCH_SIZE=100
export POSTGRES_METRICS_TABLE="app_metrics"
export POSTGRES_METRICS_METADATA_TABLE="app_metric_metadata"
export POSTGRES_SPANS_TABLE="app_spans"
export POSTGRES_SPAN_EVENTS_TABLE="app_span_events"
export POSTGRES_FLUSH_INTERVAL=5.0
```

#### 9.1.4 性能注意事项

1. **批量大小** - 根据实际负载调整批量大小，建议在50-200之间
2. **刷新间隔** - 延长刷新间隔可以减少数据库负载，但会增加内存占用
3. **索引策略** - 根据查询模式优化索引，避免过多索引影响写入性能
4. **数据清理** - 定期执行清理任务，避免表过大影响查询性能
5. **连接池大小** - 根据数据库能力配置合适的连接池大小
6. **JSONB优化** - 对于高频查询的JSONB字段，可以创建GIN索引

#### 9.1.5 查询示例

**查询指标历史数据**:

```python
# 查询HTTP请求数量
http_requests = await metrics_recorder.get_metrics_history(
    name="http_requests_total",
    start_time=datetime(2023, 1, 1),
    end_time=datetime(2023, 1, 31),
    labels={"method": "POST"},
    limit=1000
)

# 计算平均值
values = [metric["value"] for metric in http_requests]
avg_value = sum(values) / len(values) if values else 0
```

**查询追踪数据**:

```python
# 获取特定trace
trace_data = await tracer.get_trace(trace_id="abc123")

# 获取最近的traces
recent_traces = await tracer.get_recent_traces(
    limit=20,
    service_name="api-service",
    status="ERROR"
)
```

#### 9.1.6 与其他实现的集成

PostgreSQL持久化实现可以与其他实现并行使用，形成多后端写入机制:

```python
# 同时使用Prometheus和PostgreSQL
prometheus_recorder = MetricsRecorderFactory.create(
    recorder_type=MetricsRecorderType.PROMETHEUS,
    prefix="app"
)

postgres_recorder = MetricsRecorderFactory.create(
    recorder_type=MetricsRecorderType.POSTGRES,
    connection_string="postgresql://user:pass@localhost:5432/db",
    prefix="app"
)

# 创建复合记录器
recorder = CompositeMetricsRecorder([prometheus_recorder, postgres_recorder])
```

这种方式可以同时满足实时监控和历史数据分析的需求。 