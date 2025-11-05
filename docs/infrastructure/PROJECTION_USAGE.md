# OutboxProjector 使用指南

**版本**: 1.0  
**日期**: 2025-11-04

---

## 📋 概述

**OutboxProjector** 是 Bento Framework 中实现 **Transactional Outbox Pattern** 的核心组件。

它负责：
1. 从 Outbox 表轮询待发布事件
2. 通过 MessageBus 发布事件到消息总线（Pulsar/Kafka/Redis）
3. 更新事件状态（pending → publishing → published/error）

---

## 🏗️ 架构位置

```
┌─────────────────────────────────────────────────────────────┐
│              Application Layer                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │           MessageBus Port (Protocol)                │   │
│  └─────────────────────────────────────────────────────┘   │
└───────────────────────────────────────┬─────────────────────┘
                                        │ implements
                                        ↓
┌─────────────────────────────────────────────────────────────┐
│              Infrastructure Layer                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │         OutboxProjector (Background Service)        │   │
│  │  - 轮询 Outbox 表                                    │   │
│  │  - 发布到 MessageBus                                 │   │
│  │  - 更新状态                                          │   │
│  └─────────────────────────────────────────────────────┘   │
│                        ↓ uses                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │        Outbox Table (OutboxRecord)                  │   │
│  │  - status: pending → publishing → published/error   │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 💻 使用示例

### 基本使用

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from infrastructure.projection import OutboxProjector
from adapters.messaging.pulsar import PulsarEventBus

# 1. 创建 Session Factory
engine = create_async_engine(POSTGRES_DSN)
session_factory = async_sessionmaker(engine, expire_on_commit=False)

# 2. 创建 MessageBus (Pulsar/Kafka/Redis)
message_bus = PulsarEventBus(pulsar_client)

# 3. 创建 Projector
projector = OutboxProjector(
    session_factory=session_factory,
    message_bus=message_bus,
    batch_size=200  # 可选，默认 200
)

# 4. 启动（后台任务）
asyncio.create_task(projector.run_forever())
```

### 在 FastAPI 中使用

```python
from fastapi import FastAPI
from infrastructure.projection import OutboxProjector

app = FastAPI()

# 启动时
@app.on_event("startup")
async def startup():
    # 创建 projector
    projector = OutboxProjector(
        session_factory=session_factory,
        message_bus=message_bus
    )
    
    # 后台运行
    app.state.projector = projector
    asyncio.create_task(projector.run_forever())

# 关闭时
@app.on_event("shutdown")
async def shutdown():
    if hasattr(app.state, "projector"):
        await app.state.projector.stop()
```

### 在独立服务中使用

```python
import asyncio
from infrastructure.projection import OutboxProjector

async def main():
    # 创建 projector
    projector = OutboxProjector(
        session_factory=session_factory,
        message_bus=message_bus
    )
    
    try:
        # 运行直到停止
        await projector.run_forever()
    except KeyboardInterrupt:
        print("Stopping projector...")
        await projector.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

### 手动触发（测试场景）

```python
# 处理所有待发布事件（一次性）
projector = OutboxProjector(...)
processed_count = await projector.publish_all()
print(f"Processed {processed_count} events")
```

---

## ⚙️ 配置

### 配置常量

```python
from infrastructure.projection import (
    DEFAULT_BATCH_SIZE,  # 200
    SLEEP_BUSY,          # 0.1s (有积压时)
    SLEEP_IDLE,          # 1.0s (空闲时)
    MAX_RETRY,           # 5 (最大重试次数)
)
```

### 自定义配置

```python
projector = OutboxProjector(
    session_factory=session_factory,
    message_bus=message_bus,
    batch_size=500  # 自定义批次大小
)
```

---

## 🔄 工作流程

### 完整流程

```
1. UoW Commit
   ↓
2. 领域事件写入 Outbox 表 (status='pending')
   ↓
3. OutboxProjector 轮询 (每 0.1-5s)
   ↓
4. 查询 status='pending' 的事件
   ↓ (FOR UPDATE SKIP LOCKED)
5. 更新 status='publishing'
   ↓
6. 解析事件 (JSON → DomainEvent)
   ↓
7. 发布到 MessageBus
   ↓
8. 更新 status='published' (成功)
   或 status='pending' (失败，重试)
```

### 状态转换

```
pending → publishing → published (成功)
         ↓
         error (超过最大重试)
```

---

## 🛡️ 可靠性保证

### 1. 行级锁 (FOR UPDATE SKIP LOCKED)

- ✅ 多个 Projector 实例可以并行运行
- ✅ 不会重复处理同一事件
- ✅ 支持水平扩展

### 2. 事务保证

- ✅ 查询、更新在同一事务中
- ✅ 发布失败不会丢失事件
- ✅ 状态更新原子性

### 3. 重试机制

- ✅ 发布失败时标记为 pending（重试）
- ✅ 记录错误日志
- ✅ 支持手动干预

### 4. 自适应休眠

- ✅ 有积压：快速轮询 (0.1s)
- ✅ 空闲：指数退避 (1s → 5s)

---

## 📊 监控和调试

### 日志

```python
# 查看日志
logger = logging.getLogger("infrastructure.projection")

# 日志级别
- INFO: 启动、停止、批量处理
- DEBUG: 每次轮询详情
- WARNING: 发布失败
- ERROR: 解析错误、系统错误
```

### 关键指标

```python
# 可以添加的监控指标：
- outbox_pending_count: 待发布事件数
- outbox_published_count: 已发布事件数
- outbox_error_count: 错误事件数
- outbox_publish_duration: 发布耗时
```

### 查询 Outbox 表

```sql
-- 查看待发布事件
SELECT COUNT(*) FROM outbox_record WHERE status = 'pending';

-- 查看错误事件
SELECT * FROM outbox_record WHERE status = 'error';

-- 查看发布历史
SELECT * FROM outbox_record 
WHERE status = 'published' 
ORDER BY id DESC 
LIMIT 100;
```

---

## 🔧 故障处理

### 常见问题

#### 1. 事件积压

**现象**: 待发布事件持续增长

**解决方案**:
- 增加 Projector 实例（水平扩展）
- 增加 batch_size
- 检查 MessageBus 连接

#### 2. 发布失败

**现象**: 大量 status='error' 事件

**解决方案**:
- 检查 MessageBus 配置
- 检查网络连接
- 手动重置错误事件：

```sql
UPDATE outbox_record 
SET status = 'pending' 
WHERE status = 'error';
```

#### 3. 重复发布

**现象**: 同一事件被发布多次

**解决方案**:
- 确保 MessageBus 实现幂等性
- 检查事务隔离级别
- 使用 `FOR UPDATE SKIP LOCKED` (已实现)

---

## 🎯 最佳实践

### 1. 部署建议

- ✅ **多实例部署**: 运行多个 Projector 实例提高吞吐
- ✅ **独立服务**: 可以部署为独立的微服务
- ✅ **容器化**: 使用 Docker/Kubernetes 管理

### 2. 配置建议

- ✅ **Batch Size**: 根据事件大小和网络延迟调整 (100-500)
- ✅ **Sleep Interval**: 根据事件产生频率调整
- ✅ **监控告警**: 设置待发布事件数告警

### 3. 错误处理

- ✅ **手动干预**: 定期检查错误事件
- ✅ **重试策略**: 实现更复杂的重试逻辑（如果 OutboxRecord 支持 retry_cnt）
- ✅ **告警机制**: 错误事件超过阈值时告警

---

## 📝 总结

**OutboxProjector** 是事件驱动架构的核心组件，提供了：

- ✅ **可靠的事件投递**: 保证事件最终一致性
- ✅ **高性能**: 批量处理和并发安全
- ✅ **可扩展**: 支持水平扩展
- ✅ **易监控**: 清晰的状态和日志

**使用场景**:
- ✅ 所有使用 Outbox Pattern 的项目
- ✅ 需要可靠事件投递的场景
- ✅ 微服务架构中的事件总线集成

---

**OutboxProjector 让事件驱动架构更加可靠！** 🚀

