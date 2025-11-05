# DDD × SQLAlchemy × Outbox 完整方案白皮书  
*(基于本次讨论的最终形态，供团队评审 / On-boarding / 运维落地)*  

---

## 1 整体蓝图  

```
Command          UoW                拦截器链                数据库
──────── ▶  SqlAlchemyAsyncUoW ── after_flush (Outbox) ──┐
│                        ▲                              │
│                        │ flush + commit               │
└─── EventBus publish ◀──┘                              │
                                                       outbox 表 (NEW/SENT)

Projection/CDC ▶ 读库 / 消息总线 / 第三方集成
```

| 层级 | 核心职责 | 关键实现 |
|------|----------|----------|
| **聚合** | 业务行为 + `raise_event()` | `RoutePlan`, `RoutePlanCreated`… |
| **仓储** | RepoAdapter → `SaBaseRepository` | 拦截器：缓存、多租户、软删、审计 |
| **Unit-of-Work** | 事务边界、事件收集、Outbox 一致性、Tenacity 重试发布 | `unit_of_work.py` |
| **Outbox 拦截器** | `after_flush` 写入 `outbox` 行，事务内与业务表原子提交 | `persist_events()` |
| **Projector / 轮询器** | 读取 status=NEW 行 → 发送消息 → 标记 SENT | 可水平扩展、幂等 |

---

## 2 核心代码一览  

### 2.1 异步 UoW (精简)

```python
class SqlAlchemyAsyncUoW(AbstractUnitOfWork[AR]):
    async def begin(self):
        self._session = self._sf()
        self._session.info["uow"] = self          # back-link

    async def _do_commit(self):
        await self._session.commit()              # flush + 写 outbox

    async def commit(self):
        events = self._collect_events()
        await self._do_commit()                   # 原子提交
        if events:
            await self._publish_with_retry(events)  # 指数退避 3 次
```

*Tenacity* 重试，失败落日志不回滚（**at-least-once**）。

### 2.2 Outbox PO & Listener

```python
class OutboxPO(Base):
    id = Column(UUID, primary_key=True, default=uuid4)
    type = Column(String(128)); payload = Column(JSONB)
    status = Column(String(10), default="NEW")
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

@event.listens_for(Session, "after_flush")
def persist_events(sess, *_):
    uow = sess.info.get("uow");  events = uow._collect_events()
    for e in events: sess.add(OutboxPO.from_domain(e))
```

### 2.3 Projector (简易轮询)

```python
async def projector(sf):
    while True:
        async with sf() as s, s.begin():
            rows = (await s.scalars(select(OutboxPO)
                       .where(OutboxPO.status=="NEW")
                       .limit(100).with_for_update(skip_locked=True))).all()
            for po in rows:
                await bus.publish([po.payload])   # 幂等
                po.status = "SENT"
        await asyncio.sleep(1)
```

---

## 3 优劣权衡  

| 优点 | 说明 |
|------|------|
| **强一致** | 业务表 + outbox 同事务，永不丢事件 |
| **低延迟** | UoW 尝试实时发布，失败由 Projector 兜底 |
| **异步高并发** | 单层事务，仓储拦截器处理多租户/软删/乐观锁 |
| **易扩展** | Tenancy、缓存、审计、指标都在拦截器链可插拔 |

| 注意 | 对策 |
|------|------|
| 发布三次仍失败 → 事件卡 NEW | Prometheus 报警；Projector 定时重试 |
| Outbox 表膨胀 | `status=SENT AND created_at<90d` 定期归档 |
| 批量脚本 | 用 `session.begin_nested()` 分批   |
| 幂等消费 | 事件载 `event_id`；下游按键去重 |

---

## 4 落地 Checklist  

- [ ] Alembic migration 创建 `outbox`、业务表联合索引 `(tenant_id,id)`
- [ ] Prom-metrics：`outbox_new`, `publish_retry_total`, `publish_failure_total`
- [ ] Terraform / Helm：Projector 部署副本数=N，`skip_locked` 保证不重复
- [ ] Chaos test：断开 Broker 5 s，验证数据不丢 & 自动恢复
- [ ] 文档：新人需阅读 **聚合→仓储→UoW→Outbox** 流程图

---

## 5 结论  

> 通过 **异步 UoW + Outbox 拦截器 + Tenacity 重试 + Projector**  
> - 解决了**双写不一致**、**低延迟**、**最终可靠**三难题  
> - 仍保持代码层次清晰、业务零侵入  

这就是本轮讨论形成的 **完整、可落地的 Outbox 架构方案**。  
如需进一步示例（多租户 Projector 分片、Kafka Exactly-Once、Prometheus dashboard），随时找我！