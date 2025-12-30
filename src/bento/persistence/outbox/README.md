# Outbox Pattern

事务性事件发布模式，确保发送端的 exactly-once 语义。

## 概述

Outbox Pattern 解决了"数据库事务"和"消息发布"之间的一致性问题：

**问题场景**：
```python
# ❌ 危险：两个操作不在同一事务中
await repo.save(order)
await message_bus.publish(OrderCreated)  # 如果这里失败，数据已保存但事件丢失
```

**Outbox 解决方案**：
```python
# ✅ 安全：事件与数据在同一事务中
await repo.save(order)
# 事件自动写入 outbox 表（同一事务）
await uow.commit()
# Projector 异步发布事件到消息队列
```

## 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      API Layer                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │           Idempotency (命令 exactly-once)            │    │
│  │  Idempotency-Key: xxx → 缓存响应 → 重复请求返回缓存   │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   Producer Service                           │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Outbox (发送端 exactly-once)            │    │
│  │  事务内写入 outbox 表 → Projector 异步发布到消息队列  │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              ↓
                        Message Queue
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   Consumer Service                           │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Inbox (接收端 exactly-once)             │    │
│  │  检查 message_id → 跳过重复 → 处理后记录到 inbox 表   │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## 核心组件

| 组件 | 说明 |
|------|------|
| `OutboxRecord` | SQLAlchemy ORM 模型，存储待发布事件 |
| `SqlAlchemyOutbox` | Outbox 的 SQLAlchemy 实现 |
| `Outbox` | Protocol 接口定义 |
| `OutboxProjector` | 后台 Worker，从 outbox 表拉取事件并发布 |

## 使用方式

### 1. 自动模式（推荐）

通过 `SQLAlchemyUnitOfWork`，领域事件自动写入 outbox：

```python
from bento.persistence.uow import SQLAlchemyUnitOfWork

async with uow:
    # 聚合根产生事件
    order = Order.create(customer_id, items)  # 内部调用 self.add_event(OrderCreated)

    # 保存聚合根
    await uow.repository(Order).save(order)
    uow.track(order)  # 跟踪聚合根以收集事件

    # 提交时自动写入 outbox
    await uow.commit()
```

### 2. 手动模式

直接使用 `SqlAlchemyOutbox`：

```python
from bento.persistence.outbox import SqlAlchemyOutbox

outbox = SqlAlchemyOutbox(session)

# 添加事件
await outbox.add(
    topic="order.created",
    payload={"order_id": "123", "total": 99.99}
)
await session.commit()
```

### 3. Projector 配置

启动 OutboxProjector 后台服务：

```python
from bento.infrastructure.projection import OutboxProjector
from bento.adapters.messaging.pulsar import PulsarMessageBus

projector = OutboxProjector(
    session_factory=session_factory,
    message_bus=PulsarMessageBus(client),
    tenant_id="default",
)

# 启动后台任务
asyncio.create_task(projector.run_forever())
```

## 数据库表结构

```sql
CREATE TABLE outbox (
    id VARCHAR(36) PRIMARY KEY,          -- 事件 ID (UUID)
    tenant_id VARCHAR(64) NOT NULL,       -- 多租户 ID
    aggregate_id VARCHAR(128),            -- 聚合根 ID
    aggregate_type VARCHAR(100),          -- 聚合类型
    topic VARCHAR(128) NOT NULL,          -- 消息主题
    occurred_at TIMESTAMP WITH TIME ZONE, -- 事件发生时间
    payload JSON NOT NULL,                -- 事件数据
    event_metadata JSON NOT NULL,         -- 元数据
    routing_key VARCHAR(100),             -- 路由键
    schema_id VARCHAR(128),               -- Schema ID
    schema_version INTEGER DEFAULT 1,     -- Schema 版本
    status VARCHAR(10) DEFAULT 'NEW',     -- NEW/PUBLISHING/SENT/FAILED/DEAD
    retry_count INTEGER DEFAULT 0,        -- 重试次数
    retry_after TIMESTAMP WITH TIME ZONE, -- 下次重试时间
    error_message VARCHAR(500),           -- 错误信息
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 索引
CREATE INDEX ix_tenant_id_status ON outbox(tenant_id, status);
CREATE INDEX ix_outbox_processing ON outbox(status, retry_after);
CREATE INDEX ix_outbox_topic ON outbox(topic);
```

## 状态流转

```
事件产生
    ↓
  NEW (新建)
    ↓
PUBLISHING (发布中) ←─┐
    ↓                │
 发布成功?           │
  ↓    ↓            │
 是    否 ──────────┘ (重试)
  ↓           ↓
SENT       retry_count++
(已发送)        ↓
           超过最大重试?
              ↓
            DEAD (死信)
```

## Projector 工作流程

```
┌──────────────────────────────────────────────────────────┐
│                    OutboxProjector                        │
│                                                          │
│  1. 查询 status=NEW 或 (status=FAILED AND 可重试) 的事件  │
│                          ↓                               │
│  2. 使用 FOR UPDATE SKIP LOCKED 锁定行（并发安全）        │
│                          ↓                               │
│  3. 设置 status=PUBLISHING                               │
│                          ↓                               │
│  4. 发布到 MessageBus                                    │
│                          ↓                               │
│  5. 成功 → SENT，失败 → FAILED + retry_count++           │
│                          ↓                               │
│  6. 自适应休眠（有数据时短休眠，无数据时长休眠）           │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

## 配置选项

通过环境变量或 `OutboxProjectorConfig` 配置：

```python
from bento.config.outbox import OutboxProjectorConfig

config = OutboxProjectorConfig(
    batch_size=100,           # 每批处理数量
    max_retry_attempts=5,     # 最大重试次数
    sleep_busy=0.1,           # 有数据时休眠（秒）
    sleep_idle=2.0,           # 无数据时休眠（秒）
    default_tenant_id="default",
)

projector = OutboxProjector(
    session_factory=session_factory,
    message_bus=message_bus,
    config=config,
)
```

## 与其他模式的关系

| 模式 | 层级 | 用途 | 主键 |
|------|------|------|------|
| **Outbox** | 发送端 | 事务性事件发布 | event_id |
| **Inbox** | 接收端 | 消息去重 | message_id |
| **Idempotency** | API 层 | 命令幂等性 | idempotency_key |

## 设计原则

1. **事务一致性** - 事件与业务数据在同一事务中
2. **At-least-once** - Projector 保证至少发送一次
3. **顺序保证** - 同一聚合根的事件按顺序发布
4. **多租户支持** - tenant_id 字段支持租户隔离
5. **可观测性** - 状态字段便于监控和排障

## 监控指标

建议监控以下指标：

| 指标 | 说明 | 告警阈值 |
|------|------|---------|
| `outbox_backlog` | NEW 状态事件数量 | > 1000 |
| `outbox_failed` | FAILED 状态数量 | > 10 |
| `outbox_dead` | DEAD 状态数量 | > 0 |
| `outbox_publish_latency` | 发布延迟 | > 5s |

## 常见问题

### Q: 事件重复发送怎么办？
A: 消费端使用 **Inbox Pattern** 进行去重。

### Q: Projector 崩溃会丢失事件吗？
A: 不会。事件已持久化到 outbox 表，Projector 重启后继续处理。

### Q: 如何处理死信？
A: DEAD 状态的事件需要人工介入。可以：
1. 修复问题后重置 status=NEW
2. 查看 error_message 分析原因
3. 手动重放或删除

### Q: 如何清理已发送的事件？
A: 定期清理 SENT 状态的旧记录：
```python
DELETE FROM outbox
WHERE status = 'SENT'
AND created_at < NOW() - INTERVAL '7 days';
```
