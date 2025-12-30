# Inbox Pattern

消息去重模式，确保消息接收端的 exactly-once 处理。

## 概述

Inbox Pattern 是 Outbox Pattern 的对偶：
- **Outbox**: 确保发送端 exactly-once（事务性发送）
- **Inbox**: 确保接收端 exactly-once（消息去重）

## 核心组件

| 组件 | 说明 |
|------|------|
| `InboxRecord` | SQLAlchemy ORM 模型，存储已处理的消息 ID |
| `SqlAlchemyInbox` | Inbox 的 SQLAlchemy 实现 |
| `Inbox` | Protocol 接口定义 |

## 使用方式

### 1. 在消息处理器中使用

```python
from bento.persistence.inbox import SqlAlchemyInbox

class OrderEventHandler:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.inbox = SqlAlchemyInbox(session, tenant_id="default")

    async def handle_order_created(self, event_id: str, payload: dict):
        # 1. 检查是否已处理（幂等性检查）
        if await self.inbox.is_processed(event_id):
            logger.info(f"Skipping duplicate event: {event_id}")
            return

        # 2. 执行业务逻辑
        await self.process_order(payload)

        # 3. 标记为已处理（在同一事务中）
        await self.inbox.mark_processed(
            message_id=event_id,
            event_type="OrderCreated",
            payload=payload,
            source="order-service",
        )

        # 4. 提交事务（业务数据 + inbox 记录一起提交）
        await self.session.commit()
```

### 2. 与 MessageEnvelope 配合使用

```python
from bento.messaging import MessageEnvelope, Inbox

async def handle_message(envelope: MessageEnvelope, inbox: Inbox):
    # 使用 envelope.event_id 作为去重键
    if await inbox.is_processed(envelope.event_id):
        return  # 跳过重复消息

    # 处理消息
    await process_business_logic(envelope.payload)

    # 标记已处理
    await inbox.mark_processed(
        message_id=envelope.event_id,
        event_type=envelope.event_type,
        payload=envelope.payload,
    )
```

## 数据库表结构

```sql
CREATE TABLE inbox (
    message_id VARCHAR(36) PRIMARY KEY,  -- 消息 ID（主键）
    tenant_id VARCHAR(64) NOT NULL,       -- 多租户 ID
    event_type VARCHAR(128) NOT NULL,     -- 事件类型
    source VARCHAR(128),                  -- 来源服务
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    payload_hash VARCHAR(64),             -- 负载哈希（调试用）
    extra_data JSON                       -- 额外数据
);

-- 索引
CREATE INDEX ix_inbox_tenant_event ON inbox(tenant_id, event_type);
CREATE INDEX ix_inbox_processed_at ON inbox(processed_at);
```

## 清理策略

Inbox 记录会随时间累积，建议定期清理：

```python
# 清理 30 天前的记录
deleted_count = await inbox.cleanup_old_records(older_than_days=30)
logger.info(f"Cleaned up {deleted_count} old inbox records")
```

可以通过定时任务或后台 worker 执行清理。

## 设计原则

1. **同一事务** - `mark_processed` 必须与业务逻辑在同一事务中
2. **主键去重** - 使用 `message_id` 作为主键，数据库层面保证唯一
3. **多租户支持** - `tenant_id` 字段支持租户隔离
4. **可审计** - 保留 `payload_hash` 和 `extra_data` 用于调试

## 与 Outbox 的配合

```
Producer Service                    Consumer Service
┌─────────────────┐                ┌─────────────────┐
│  Business Logic │                │  Business Logic │
│        ↓        │                │        ↑        │
│    Outbox       │ ──Message──>   │     Inbox       │
│   (exactly-once │                │  (exactly-once  │
│     sending)    │                │   processing)   │
└─────────────────┘                └─────────────────┘
```

## API 参考

### `SqlAlchemyInbox`

```python
class SqlAlchemyInbox:
    def __init__(self, session: AsyncSession, tenant_id: str = "default"):
        """初始化 Inbox"""

    async def is_processed(self, message_id: str) -> bool:
        """检查消息是否已处理"""

    async def mark_processed(
        self,
        message_id: str,
        event_type: str,
        payload: dict | None = None,
        source: str | None = None,
        extra_data: dict | None = None,
    ) -> InboxRecord:
        """标记消息为已处理"""

    async def get_record(self, message_id: str) -> InboxRecord | None:
        """获取 Inbox 记录"""

    async def cleanup_old_records(self, older_than_days: int = 30) -> int:
        """清理旧记录"""
```
