# Observability Listeners

这个目录包含了用于监控数据库操作、缓存操作和消息队列的监听器，为这些基础设施组件提供性能监控和分布式追踪能力。

## 可用的监听器

1. **SQLAlchemyListener**: 用于监控 SQLAlchemy 数据库操作
2. **CacheListener**: 用于监控 Redis、Memcached 等缓存操作
3. **MessagingListener**: 用于监控 Kafka、RabbitMQ、Pulsar 等消息队列操作

## 使用方法

### SQLAlchemy 监听器

用于监控数据库操作性能和异常：

```python
from idp.framework.infrastructure.observability import SQLAlchemyListener
from idp.framework.infrastructure.observability.metrics import PrometheusRecorder
from idp.framework.infrastructure.observability.tracing import MemoryTracer
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine

# 同步引擎
engine = create_engine("postgresql://user:pass@localhost/dbname")
listener = SQLAlchemyListener.install(
    engine,
    metrics_recorder=PrometheusRecorder.get_instance("my-service"),
    tracer=MemoryTracer("my-service")
)

# 异步引擎
async_engine = create_async_engine("postgresql+asyncpg://user:pass@localhost/dbname")
listener = SQLAlchemyListener.install(
    async_engine,
    metrics_recorder=PrometheusRecorder.get_instance("my-service"),
    tracer=MemoryTracer("my-service")
)
```

### 缓存监听器

用于监控缓存操作的命中率、性能和异常：

```python
from idp.framework.infrastructure.observability import CacheListener
from idp.framework.infrastructure.observability.metrics import PrometheusRecorder
from idp.framework.infrastructure.observability.tracing import MemoryTracer
import redis

# Redis 示例
redis_client = redis.Redis(host='localhost', port=6379, db=0)
listener = CacheListener.install(
    redis_client,
    metrics_recorder=PrometheusRecorder.get_instance("my-service"),
    tracer=MemoryTracer("my-service"),
    cache_name="main-redis"
)

# 使用被监控的客户端
value = redis_client.get("my-key")  # 这个操作会被自动监控
```

### 消息队列监听器

用于监控消息发布、消费和处理的性能：

```python
from idp.framework.infrastructure.observability import MessagingListener
from idp.framework.infrastructure.observability.metrics import PrometheusRecorder
from idp.framework.infrastructure.observability.tracing import MemoryTracer
from kafka import KafkaProducer, KafkaConsumer

# Kafka 生产者
producer = KafkaProducer(bootstrap_servers='localhost:9092')
listener = MessagingListener.install_kafka_producer(
    producer,
    metrics_recorder=PrometheusRecorder.get_instance("my-service"),
    tracer=MemoryTracer("my-service")
)

# 发送消息（会被自动监控）
producer.send('my-topic', b'message value')

# Kafka 消费者
consumer = KafkaConsumer('my-topic', group_id='my-group')
listener = MessagingListener.install_kafka_consumer(
    consumer,
    metrics_recorder=PrometheusRecorder.get_instance("my-service"),
    tracer=MemoryTracer("my-service"),
    consumer_group='my-group'
)

# 消息消费也会被自动监控
for message in consumer:
    process_message(message)
```

## 监控指标

每个监听器都会记录以下类型的指标：

### 数据库监听器

- `db_operation_duration_seconds`: 操作持续时间直方图
- `db_errors_total`: 错误计数
- `db_affected_rows_total`: 受影响行数
- `db_rollbacks_total`: 回滚计数

### 缓存监听器

- `cache_hits_total`: 缓存命中计数
- `cache_misses_total`: 缓存未命中计数 
- `cache_operation_duration_seconds`: 操作持续时间直方图
- `cache_errors_total`: 错误计数

### 消息队列监听器

- `message_published_total`: 已发布消息计数
- `message_consumed_total`: 已消费消息计数
- `message_processing_duration_seconds`: 处理持续时间直方图
- `message_publish_errors_total`: 发布错误计数
- `message_consume_errors_total`: 消费错误计数

## 分布式追踪

所有监听器都支持创建和传播 Span，使用 ITracer 接口：

- 每个数据库操作都会创建一个 `CLIENT` 类型的 Span
- 每个缓存操作都会创建一个 `CLIENT` 类型的 Span
- 消息发布会创建一个 `PRODUCER` 类型的 Span
- 消息消费会创建一个 `CONSUMER` 类型的 Span

追踪上下文会在分布式系统中自动传播，确保全链路可见性。 