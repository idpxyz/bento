# Bento Outbox 智能路由指南

## 🎯 概述

Bento Framework 的 Outbox 模块现已支持智能路由配置，提供企业级的事件分发能力。

### 核心特性

✅ **简单路由** - 单目标快速路由
✅ **条件路由** - 基于事件内容的动态路由
✅ **采样路由** - 按比例采样分发
✅ **延迟投递** - 支持延时处理
✅ **数据转换** - 字段过滤和映射
✅ **指数退避** - 智能重试机制
✅ **多租户** - 租户隔离支持

## 📊 数据库字段

```sql
-- 新增字段（完整迁移版本）
ALTER TABLE outbox ADD COLUMN topic VARCHAR(128) NOT NULL;           -- 事件主题
ALTER TABLE outbox ADD COLUMN occurred_at TIMESTAMP NOT NULL;         -- 发生时间
ALTER TABLE outbox ADD COLUMN aggregate_type VARCHAR(100);            -- 聚合类型
ALTER TABLE outbox ADD COLUMN metadata JSONB DEFAULT '{}';            -- 元数据
ALTER TABLE outbox ADD COLUMN routing_key VARCHAR(100);              -- 简单路由
ALTER TABLE outbox ADD COLUMN routing_config JSONB DEFAULT '{}';     -- 智能路由
ALTER TABLE outbox ADD COLUMN routing_version INTEGER DEFAULT 1;     -- 路由版本
ALTER TABLE outbox ADD COLUMN retry_after TIMESTAMP;                 -- 重试时间
ALTER TABLE outbox ADD COLUMN error_message VARCHAR(500);            -- 错误信息
```

## 🚀 快速开始

### 1. 简单路由

```python
from bento.persistence.outbox import OutboxRecord

# 创建事件
event = ProductCreatedEvent(...)

# 简单路由
record = OutboxRecord.from_domain_event(event)
record.routing_key = "catalog.product.created"
```

### 2. 智能路由

```python
from bento.persistence.outbox import RoutingConfigBuilder

# 配置智能路由
routing_config = (
    RoutingConfigBuilder()
    .add_target(
        destination="search.index",
        conditions={"payload.visible": True}
    )
    .add_target(
        destination="vip.notifications",
        conditions={"payload.price": {"$gt": 1000}},
        transform={"include_fields": ["id", "name", "price"]}
    )
    .set_fallback("default.events")
    .build()
)

# 创建记录
record = OutboxRecord.from_domain_event(event, routing_config)
```

### 3. 事件处理

```python
from bento.persistence.outbox import create_outbox_processor

# 创建处理器
processor = create_outbox_processor(
    session=db_session,
    publisher_type="console",  # 或 "kafka"
    batch_size=100
)

# 处理事件
await processor.process_events(tenant_id="shop-001")

# 或启动轮询
await processor.start_polling(interval_seconds=5)
```

## 🔧 路由配置详解

### 条件语法

```python
conditions = {
    "payload.price": {"$gt": 1000},           # 大于
    "payload.category": {"$in": ["electronics", "books"]}, # 包含
    "payload.visible": True,                   # 等于
    "aggregate_type": {"$ne": "User"},        # 不等于
    "tenant_id": {"$exists": True}            # 存在
}
```

### 数据转换

```python
transform = {
    "include_fields": ["id", "name", "price"],        # 只包含指定字段
    "exclude_fields": ["internal_notes"],             # 排除字段
    "field_mapping": {"total": "order_value"},        # 字段重命名
    "add_fields": {"source": "outbox"}               # 添加字段
}
```

### 高级配置

```python
routing_config = {
    "targets": [
        {
            "destination": "high_priority.queue",
            "conditions": {"payload.urgent": True},
            "delay_seconds": 0,
            "sampling_rate": 1.0,
            "retry_policy": "aggressive"
        }
    ],
    "strategy": "all_or_nothing",  # 或 "best_effort"
    "fallback": "dead_letter_queue"
}
```

## 📈 性能优化

### 索引配置

```sql
-- 处理队列索引
CREATE INDEX idx_outbox_processing ON outbox_events (status, retry_after);

-- 租户索引
CREATE INDEX idx_outbox_tenant ON outbox_events (tenant_id, status);

-- 主题索引
CREATE INDEX idx_outbox_topic ON outbox_events (topic);

-- 聚合索引
CREATE INDEX idx_outbox_aggregate ON outbox_events (aggregate_type, aggregate_id);
```

### 批量处理

```python
# 配置批量大小
processor = OutboxProcessor(
    session=session,
    publisher=publisher,
    batch_size=500,  # 增大批次提升性能
    max_retry=3      # 减少重试次数
)
```

## 🛠️ 自定义发布器

```python
from bento.persistence.outbox import EventPublisher

class CustomEventPublisher:
    async def publish(self, destination: str, payload: dict, metadata: dict) -> bool:
        # 实现您的发布逻辑
        # 例如：发送到 Kafka、RabbitMQ、HTTP webhook 等
        print(f"Publishing to {destination}: {payload}")
        return True

# 使用自定义发布器
processor = OutboxProcessor(
    session=session,
    publisher=CustomEventPublisher()
)
```

## 🔍 监控和调试

### 状态查询

```sql
-- 查看各状态事件数量
SELECT status, COUNT(*) FROM outbox_events GROUP BY status;

-- 查看失败事件
SELECT * FROM outbox_events WHERE status = 'FAILED' ORDER BY retry_count DESC;

-- 查看死信队列
SELECT * FROM outbox_events WHERE status = 'DEAD';
```

### 日志配置

```python
import logging

# 启用详细日志
logging.getLogger("bento.persistence.outbox").setLevel(logging.DEBUG)
```

## 📋 最佳实践

### 1. 路由策略选择

```python
# ✅ 简单场景：使用 routing_key
record.routing_key = "orders.created"

# ✅ 条件路由：基于业务逻辑
routing_config = create_conditional_routing([
    ("urgent.processing", {"payload.priority": "high"}),
    ("normal.processing", {"payload.priority": "normal"})
])

# ✅ 大流量：使用采样
routing_config = create_sampling_routing("analytics.events", 0.1)
```

### 2. 性能优化

```python
# ✅ 批量处理
processor.batch_size = 500

# ✅ 合理的轮询间隔
await processor.start_polling(interval_seconds=2)

# ✅ 限制重试次数
processor.max_retry = 3
```

### 3. 错误处理

```python
# ✅ 设置降级策略
routing_config = (
    RoutingConfigBuilder()
    .add_target("primary.service")
    .set_fallback("backup.service")  # 主服务失败时的备选
    .build()
)

# ✅ 监控死信队列
dead_events = await session.execute(
    select(OutboxRecord).where(OutboxRecord.status == "DEAD")
)
```

### 4. 多租户隔离

```python
# ✅ 按租户处理
await processor.process_events(tenant_id="tenant-001")

# ✅ 租户级监控
tenant_stats = await session.execute(
    select(OutboxRecord.status, func.count())
    .where(OutboxRecord.tenant_id == "tenant-001")
    .group_by(OutboxRecord.status)
)
```

## 🎯 总结

Bento Outbox 智能路由提供了：

- **🚀 高性能**：批量处理 + 优化索引
- **🎛️ 灵活配置**：条件路由 + 数据转换
- **🔄 可靠投递**：重试机制 + 死信队列
- **📊 可观测**：状态跟踪 + 错误记录
- **🏢 企业级**：多租户 + 版本管理

立即开始使用智能路由，提升您的事件驱动架构！
