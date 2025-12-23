# Idempotency Pattern

命令幂等性模式，确保 API 请求的 exactly-once 执行。

## 概述

Idempotency Pattern 与 Inbox Pattern 的区别：
- **Inbox**: 消息级去重（基于 event_id）
- **Idempotency**: 命令级去重（基于客户端提供的 Idempotency-Key）

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

## 核心组件

| 组件 | 说明 |
|------|------|
| `IdempotencyRecord` | SQLAlchemy ORM 模型 |
| `SqlAlchemyIdempotency` | Idempotency 的 SQLAlchemy 实现 |
| `IdempotencyStore` | Protocol 接口定义 |
| `IdempotencyConflictError` | 冲突异常 |

## 使用方式

### 1. 在 API Handler 中使用

```python
from fastapi import Header
from bento.persistence.idempotency import SqlAlchemyIdempotency

@app.post("/orders", status_code=201)
async def create_order(
    command: CreateOrderCommand,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    session: AsyncSession = Depends(get_session),
):
    if not idempotency_key:
        # 无幂等键，正常处理
        return await handler.execute(command)

    idempotency = SqlAlchemyIdempotency(session)

    # 1. 检查是否已有缓存响应
    cached = await idempotency.get_response(idempotency_key)
    if cached:
        return JSONResponse(
            content=cached.response,
            status_code=cached.status_code,
        )

    # 2. 锁定 key（防止并发处理）
    await idempotency.lock(
        idempotency_key=idempotency_key,
        operation="CreateOrder",
        request_hash=hash_request(command),
    )

    try:
        # 3. 执行业务逻辑
        result = await handler.execute(command)

        # 4. 存储响应
        await idempotency.store_response(
            idempotency_key=idempotency_key,
            response=result.to_dict(),
            status_code=201,
        )
        await session.commit()

        return result

    except Exception as e:
        # 5. 标记失败（允许重试）
        await idempotency.mark_failed(idempotency_key)
        await session.commit()
        raise
```

### 2. 使用装饰器（推荐）

```python
from bento.application.decorators import idempotent

@idempotent(operation="CreateOrder")
@command_handler
class CreateOrderHandler(CommandHandler[CreateOrderCommand, Order]):
    async def handle(self, command: CreateOrderCommand) -> Order:
        # 业务逻辑
        ...
```

## 数据库表结构

```sql
CREATE TABLE idempotency (
    idempotency_key VARCHAR(64) PRIMARY KEY,  -- 客户端提供的 key
    tenant_id VARCHAR(64) NOT NULL,            -- 多租户 ID
    operation VARCHAR(128) NOT NULL,           -- 操作名称
    request_hash VARCHAR(64),                  -- 请求哈希（冲突检测）
    response JSON,                             -- 缓存的响应
    status_code INTEGER DEFAULT 200,           -- HTTP 状态码
    state VARCHAR(20) DEFAULT 'PENDING',       -- PENDING/COMPLETED/FAILED
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE        -- 过期时间
);

-- 索引
CREATE INDEX ix_idempotency_tenant ON idempotency(tenant_id);
CREATE INDEX ix_idempotency_expires ON idempotency(expires_at);
```

## 状态流转

```
客户端请求 (带 Idempotency-Key)
        ↓
    检查 key 是否存在
        ↓
   ┌────┴────┐
   ↓         ↓
 存在      不存在
   ↓         ↓
检查状态   创建 PENDING
   ↓         ↓
 COMPLETED  执行业务逻辑
   ↓         ↓
返回缓存   成功 → COMPLETED
响应       失败 → FAILED
```

## 冲突检测

通过 `request_hash` 检测同一 key 被不同请求复用：

```python
# 第一次请求
await idempotency.lock(
    idempotency_key="order-123",
    operation="CreateOrder",
    request_hash="abc123",  # 请求内容的哈希
)

# 第二次请求（相同 key，不同请求）
await idempotency.lock(
    idempotency_key="order-123",
    operation="CreateOrder",
    request_hash="xyz789",  # 不同的哈希
)
# 抛出 IdempotencyConflictError
```

## 清理策略

Idempotency 记录有过期时间（默认 24 小时），定期清理：

```python
# 清理过期记录
deleted_count = await idempotency.cleanup_expired()
```

## HTTP 头规范

遵循业界标准：

```http
POST /orders HTTP/1.1
Idempotency-Key: unique-request-id-123
Content-Type: application/json

{"product_id": "prod-1", "quantity": 2}
```

## 设计原则

1. **客户端控制** - 幂等 key 由客户端生成
2. **请求级别** - 不同于消息级别的 Inbox
3. **有过期时间** - 避免无限累积
4. **冲突检测** - 防止 key 被不同请求复用
5. **状态机** - PENDING → COMPLETED/FAILED

## 与其他模式的关系

| 模式 | 层级 | 用途 |
|------|------|------|
| **Outbox** | 发送端 | 事务性事件发布 |
| **Inbox** | 接收端 | 消息去重 |
| **Idempotency** | API 层 | 命令幂等性 |
