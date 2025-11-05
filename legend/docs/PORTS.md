### 在当前架构中，“领域事件 → 外部系统” 的 **Ports / Adapters** 分层

```
         ┌───────────── Domain Layer ─────────────┐
         │  ▸ 聚合 raise_event()                  │
         │  ▸ AggregateRoot.pull_events()         │
         └──────────────┬─────────────────────────┘
                        │ «Port -- 应用服务调用»
                        ▼
     ┌────────────── Application / UoW ───────────────┐
     │  SqlAlchemyAsyncUoW.commit()                   │
     │   1. _collect_events()                         │
     │   2. 写 Outbox                                 │
     │   3. ▶︎ AbstractEventBus.publish(events)  ←──┐ │
     └───────────────────┬───────────────────────────┘ │
                         │ «Port»                      │
                         ▼                             │
        infrastructure.messaging.core.event_bus        │
     ┌───────────────────────┼─────────────────────────┘
     │  🔹 AbstractEventBus  (**Port**)                │
     │       ├─ async def publish(events: Sequence[DomainEvent]) │
     │       └─ …                                      │
     │                                                  │
     │  🔸 PulsarEventBus / ConsoleBus / KafkaBus … (**Adapters**) 
     │       实现 publish → 具体 Broker API             │
     └─────────────────────────────────────────────────┘
                         ▲
                         │
        infrastructure.projection.projector (Outbox → Bus)  
        ├─ 轮询 outbox 行                                │
        └─ 同样调用 **AbstractEventBus.publish** ←───────┘
```

| 层级 | 文件/模块 | 角色 |
|------|-----------|------|
| **Port** | `infrastructure/messaging/core/event_bus.py`<br>`class AbstractEventBus` | 领域层 & UoW 依赖的接口（SPI） |
| **Primary Adapter**<br>(应用→外部) | `infrastructure/messaging/pulsar_bus.py`, `console_bus.py` … | 把 `publish()` 转成 Pulsar/Kafka/SMTP… |
| **Secondary Adapter**<br>(驱动应用) | `infrastructure/projection/projector.py` (轮询 outbox 触发) | 由外部订阅器 / scheduler 调用，驱动事件向外发送 |
| **Outbox 拦截器** | `infrastructure/persistence/sqlalchemy/interceptor/outbox_interceptor.py` | 属于持久化适配层；把领域事件写入 Outbox 表 |

### 如何接入新的外部系统？

1. **实现适配器**  
   ```python
   class WebhookEventBus(AbstractEventBus):
       async def publish(self, evts): ...
   ```
2. **在 DI 容器 / `settings.py`** 注入  
   ```python
   bus = WebhookEventBus(base_url=...)
   uow = SqlAlchemyAsyncUoW(sf, bus)
   ```
3. **（可选）Projector** 亦可多路复用  
   ```python
   async def projector(...):
       await pulsar_bus.publish(evts)
       await webhook_bus.publish(evts)
   ```

> **总结**：“Ports” 就是 `AbstractEventBus`；所有与外部总线/HTTP/队列交互的代码都放在 **infrastructure.messaging** 目录下的 **适配器** 中，而领域与应用层只依赖这个 Port，无需感知外部细节。