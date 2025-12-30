# ADR-004: Improved Outbox Database Design

## 📊 **优化后的 Outbox 表结构**

基于现有 Bento 架构和企业级需求的平衡设计。

### **表名：`outbox_events`**

```sql
CREATE TABLE outbox_events (
    -- 主键和幂等性
    id UUID PRIMARY KEY,

    -- 事件基础信息（与 DomainEvent 保持一致）
    event_topic VARCHAR(150) NOT NULL,        -- 与 DomainEvent.topic 一致
    occurred_at TIMESTAMP NOT NULL,           -- 事件发生时间
    schema_id VARCHAR(128),                   -- Schema ID
    schema_version INT NOT NULL DEFAULT 1,   -- 统一的版本字段

    -- 聚合根信息
    aggregate_id VARCHAR(128),                -- 兼容 UUID 和字符串
    aggregate_type VARCHAR(100),              -- 聚合类型 (Product, Order, etc.)

    -- 多租户和路由
    tenant_id VARCHAR(64) NOT NULL DEFAULT 'default',
    source_bc VARCHAR(50) NOT NULL,          -- 源边界上下文
    destination_topics JSONB,                -- 目标 topics（可选）

    -- 事件数据
    payload JSONB NOT NULL,                   -- 事件数据
    metadata JSONB,                          -- 元数据（trace_id, user_id, etc.）

    -- 状态管理
    status VARCHAR(10) NOT NULL DEFAULT 'NEW',    -- NEW, SENT, FAILED, DEAD
    retry_count INT NOT NULL DEFAULT 0,
    next_retry_at TIMESTAMP,                  -- 下次重试时间
    error_message TEXT,                       -- 错误信息

    -- 时间戳
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMP                    -- 处理完成时间
);

-- 索引优化
CREATE INDEX idx_outbox_status ON outbox_events (status, next_retry_at);
CREATE INDEX idx_outbox_tenant_status ON outbox_events (tenant_id, status);
CREATE INDEX idx_outbox_created ON outbox_events (created_at);
CREATE INDEX idx_outbox_aggregate ON outbox_events (aggregate_type, aggregate_id);
CREATE INDEX idx_outbox_topic ON outbox_events (event_topic);
```

## 🔄 **与现有架构的兼容性**

### **保持的字段**
- ✅ `id` - 主键
- ✅ `tenant_id` - 多租户支持
- ✅ `aggregate_id` - 聚合根 ID
- ✅ `payload` - 事件数据
- ✅ `status` - 状态管理
- ✅ `retry_count` - 重试次数（原 retry_cnt）
- ✅ `created_at` - 创建时间

### **新增的字段**
- 🆕 `event_topic` - 与 DomainEvent.topic 一致
- 🆕 `occurred_at` - 事件发生时间（来自 DomainEvent）
- 🆕 `aggregate_type` - 聚合类型
- 🆕 `source_bc` - 源边界上下文
- 🆕 `destination_topics` - 路由信息
- 🆕 `metadata` - 元数据支持
- 🆕 `next_retry_at` - 指数退避重试
- 🆕 `error_message` - 错误记录
- 🆕 `processed_at` - 处理时间

### **字段映射**
| 现有字段 | 新字段 | 说明 |
|---------|--------|------|
| `type` | `event_topic` | 与 DomainEvent.topic 保持一致 |
| `schema_ver` | `schema_version` | 保持现有逻辑 |
| `retry_cnt` | `retry_count` | 更规范的命名 |

## 🎯 **主要改进**

### 1. **命名一致性**
- `event_topic` 与刚刚重构的 `DomainEvent.topic` 保持一致
- 统一版本字段为 `schema_version`

### 2. **企业级特性**
- 支持跨 BC 路由（`destination_topics`）
- 指数退避重试（`next_retry_at`）
- 错误追踪（`error_message`）
- 元数据支持（`metadata`）

### 3. **与 DomainEvent 对齐**
```python
# OutboxRecord.from_domain_event() 现在可以完整映射
{
    "id": event.event_id,
    "event_topic": event.topic,           # 🆕 一致的命名
    "occurred_at": event.occurred_at,     # 🆕 事件时间
    "tenant_id": event.tenant_id,
    "aggregate_id": event.aggregate_id,
    "schema_id": event.schema_id,
    "schema_version": event.schema_version,
    "payload": event.to_payload(),
    # ... 其他字段
}
```

### 4. **向后兼容迁移策略**
```sql
-- 迁移 SQL（如果需要）
ALTER TABLE outbox
ADD COLUMN event_topic VARCHAR(150),
ADD COLUMN occurred_at TIMESTAMP,
ADD COLUMN aggregate_type VARCHAR(100),
ADD COLUMN source_bc VARCHAR(50),
ADD COLUMN destination_topics JSONB,
ADD COLUMN metadata JSONB,
ADD COLUMN next_retry_at TIMESTAMP,
ADD COLUMN error_message TEXT,
ADD COLUMN processed_at TIMESTAMP;

-- 数据迁移
UPDATE outbox SET
    event_topic = type,
    occurred_at = created_at,  -- 临时使用创建时间
    source_bc = 'default';     -- 设置默认值
```

## 💡 **使用示例**

```python
# 创建 Outbox 记录
outbox_record = OutboxRecord(
    id=str(event.event_id),
    event_topic=event.topic,              # ✅ 一致的命名
    occurred_at=event.occurred_at,
    aggregate_id=str(event.aggregate_id),
    aggregate_type="Product",
    source_bc="catalog",
    destination_topics=["product.created", "search.index"],
    payload=event.to_payload(),
    metadata={
        "trace_id": "uuid",
        "user_id": "user123"
    }
)
```

这个设计在保持企业级特性的同时，与现有 Bento 架构完美对齐！
