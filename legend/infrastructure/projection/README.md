让我检查一下 projector 的启动和运行机制。首先让我看一下 `main.py` 的完整实现：

Read file: src/idp/framework/examples/main.py
让我检查一下 OutboxProjector 的实现：

Ran tool
让我尝试使用语义搜索来定位 OutboxProjector 的实现：

Search files...
根据搜索结果，我可以为您详细解释 OutboxProjector 的实现。这是一个基于 Outbox 模式的事件投影器，用于确保领域事件的可靠传递。让我们分析其关键组件和工作原理：

### 1. 架构概览

OutboxProjector 是一个次要适配器(Secondary Adapter)，主要职责是:

1. 轮询 Outbox 表中状态为 "NEW" 的事件记录
2. 通过 EventBus 将事件发布到外部系统(如 Pulsar/Kafka)
3. 更新事件状态为 "SENT" 或 "ERR"

### 2. 核心实现

OutboxProjector 类的主要实现位于 `src/idp/framework/infrastructure/projection/projector.py`:

```python
class OutboxProjector:
    def __init__(
        self,
        sf: async_sessionmaker[AsyncSession],  # Session Factory
        bus: AbstractEventBus,                 # Event Bus 接口
        tenant_id: str,                        # 多租户分片 ID 
        batch_size: int = TRY_BATCH,          # 批处理大小
    ):
        self._sf = sf
        self._bus = bus
        self._tenant = tenant_id
        self._batch = batch_size
        self._stopped = asyncio.Event()
```

关键方法:

1. `run_forever()` - 主循环:
   - 持续轮询直到被取消
   - 处理异常并使用自适应退避策略

2. `_process_once()` - 单次处理批次:
   - 使用 `FOR UPDATE SKIP LOCKED` 锁定行
   - 将事件发布到 EventBus
   - 更新处理状态

### 3. 关键特性

1. **多租户分片**:
   - 按 `tenant_id` 水平分片
   - 每个租户独立的 Projector 实例
   - 支持水平扩展

2. **并发控制**:
   - 使用行级锁 (`FOR UPDATE SKIP LOCKED`)
   - 支持多个 Projector 实例并行处理
   - 避免重复处理

3. **可靠性保证**:
   - At-least-once 语义
   - 失败重试机制 (最多 5 次)
   - 错误状态监控

4. **性能优化**:
   - 批量处理 (默认 200 条)
   - 自适应休眠 (有积压 0.1s, 空闲 1.0s)
   - 事务管理

### 4. Outbox 表结构

```sql
CREATE TABLE outbox (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    type VARCHAR(128) NOT NULL,
    payload JSONB NOT NULL,
    status VARCHAR(10) DEFAULT 'NEW',
    retry_cnt INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX ix_tenant_id_status ON outbox(tenant_id, status);
```

### 5. 使用示例

```python
# FastAPI startup
engine = create_async_engine(POSTGRES_DSN)
sf = async_sessionmaker(engine, expire_on_commit=False)

bus = PulsarEventBus(pulsar_client, topic_template="tenant-{tenant}")
projector = OutboxProjector(sf, bus, tenant_id="t1")
asyncio.create_task(projector.run_forever())
```

### 6. 错误处理和监控

1. 重试机制:
   - 发布失败时增加重试计数
   - 超过最大重试次数(5次)标记为 "ERR"
   - 支持手动/自动重置错误状态

2. 监控指标:
   - NEW 事件数量
   - 重试次数
   - 错误率
   - 处理延迟

这个实现提供了一个可靠的事件发布机制，确保了领域事件的最终一致性传递，同时支持多租户和水平扩展。

**Projector**（在我们的架构里通常指 **OutboxProjector**）的核心目的与价值，是在**写事务**与**事件总线**之间，构建一条**可靠的异步投递通道**，具体表现在以下几点：

1. **事务与消息的解耦**  
   - **写操作**：业务数据和 Outbox 行在同一个数据库事务里一起提交，保证“要么都成功、要么都回滚”。  
   - **投递操作**：由 Projector 在事务之外、独立地异步读取 Outbox 表并推送消息。  
   - 这样，消息投递的失败不会影响业务写入，也不会丢失事件。

2. **最终一致性保证**  
   - 即使应用进程宕机、网络抖动或实时发布失败，Outbox 表里仍保留 `status='NEW'` 的事件行。  
   - Projector 以 **定期轮询**（`FOR UPDATE SKIP LOCKED`）的方式重试，直到投递成功或达到最大重试次数并打标 `ERR`。  
   - 确保事件至少被投递一次，实现*至少一次*或在支持事务的总线上*恰好一次*。

3. **可横向扩展的多租户投递**  
   - 按 `tenant_id` 启动多路 Projector 实例或 Pod，利用数据库行锁 (`SKIP LOCKED`) 并发安全地分片处理。  
   - 支持海量租户场景，每个租户独立投递主题，不会互相干扰。

4. **监控与告警**  
   - 可在 Projector 中埋点（Prometheus Counter/Gauge），监控“待投递队列长度”、“投递成功率”、“异常行数”。  
   - 当某条事件多次投递失败（`retry_cnt >= MAX_RETRY`）时，可触发告警并人工干预。

5. **兼容 CQRS 读模型投影**  
   - 虽然核心职责是“落地消息 → 推送总线”，Projector 同样可以在投递前 **直接更新本地读库**（即读模型），完成 CQRS 里的 Projection 职能。  
   - 也可与外部消息消费者并行：Projector 通常负责“出站”投递，另一套消费者负责“入站”更新多视图。

---

### 总结

> **Projector = Transactional Outbox 的异步推送执行器**。  
> 它保证业务写入和消息投递解耦，提供强可靠、可伸缩的**事件分发**能力，并为上游提供监控告警和 CQRS 投影的基础。

In event-driven and CQRS architectures, a **“projector”** is any component that takes a stream of domain events and “projects” them into some other form—be that messages on a bus, rows in a read‐optimized table, documents in a search index, metrics in Prometheus, or notifications to users. Here are a few common flavors beyond the OutboxProjector:

---

## 常见的 Projector 类型

1. **Read-Model Projector (Query-Side)**
   - **职责**：把事件应用到一组专门的“查询表”或“视图”  
   - **技术**：关系型表、Redis、MongoDB、DynamoDB  
   - **用途**：为不同的 UI/报表场景提供预计算、去联表后的快速读访问  

2. **Search-Index Projector**
   - **职责**：将事件映射为可全文检索的文档  
   - **技术**：Elasticsearch、OpenSearch  
   - **用途**：支持模糊搜索、打分排名、地理位置查询等  

3. **Analytics / Aggregate-Stats Projector**
   - **职责**：累积或叠加事件数据生成实时统计  
   - **技术**：Kafka Streams、Flink、Materialized Views  
   - **用途**：实时仪表盘、汇总指标（如订单量、活跃用户数）  

4. **Notification Projector**
   - **职责**：对特定事件触发邮件、短信、WebHook 等外部通知  
   - **技术**：SMTP、Twilio、Serverless 函数  
   - **用途**：及时提醒用户——例如订单已发货、任务已超时  

5. **Audit-Log Projector**
   - **职责**：把事件写入专门的审计存储，支持历史回溯和合规查询  
   - **技术**：Append-only 日志数据库、专门的审计表  
   - **用途**：GDPR 合规、法务取证  

6. **Materialized View Projector**
   - **职责**：在数据库内部维护物化视图（Materialized View）  
   - **技术**：PostgreSQL MV、ClickHouse  
   - **用途**：大规模聚合或预计算，进一步加速复杂查询  

7. **Graph-Model Projector**
   - **职责**：将事件投影到图数据库节点和边上  
   - **技术**：Neo4j、JanusGraph  
   - **用途**：社交关系网、权限继承树、推荐系统  

8. **Hybrid / Fan-out Projector**
   - **职责**：同一事件既更新本地读模型，也发往多个总线或外部系统  
   - **用途**：多渠道同步，多系统最终一致  

---

## 为什么叫 “投影”（Projection）？

“Projection” 一词来源于数学和数据库领域：

- **数学投影**：将高维数据映射到低维空间，例如从三维空间投影到二维平面。  
- **数据库投影**（SQL 中的 `SELECT a, b FROM T`）指从一行中“投出”部分字段。  
- **事件投影**：把一连串的事件“映射”或“投射”成另一种数据表示——可能是状态快照、报告表、索引文档、消息等。

在 **Event-Sourcing/CQRS** 中，**事件本身是事实**，而 **投影**（Projector）就是把这些事实“投”到不同的“视图”（View）或“模型”（Model）中，服务于不同的查询、统计、集成或通知需求。

---

### 小结

- **OutboxProjector** 负责“事件 → 消息总线”  
- **Read-Model Projector** 负责“事件 → 查询表”  
- **Search-Index/Analytics/Notification/Audit…** Projector 各司其职  

一旦你把投影逻辑以独立、可复用的组件拆分出来，就能针对不同场景（读性能、搜索、监控、通知）灵活组合和扩展，而不影响核心的写事务和领域模型。