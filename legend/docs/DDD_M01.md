下面针对你提供的 `SqlAlchemyAsyncUoW` 实现（见 infra/uow/unit_of_work.py）做一次评估，看看它与我们之前讨论的 DDD+CQRS UoW 设计要点的契合度，并给出一些改进建议。

------

## 一、符合的关键要点

1. **统一会话管理**
   - 通过在 `__aenter__`／`__aexit__` 中调用 `begin()`、`commit()`、`rollback()`、`_cleanup()`，保证了整个 `with` 语境下使用同一个 `AsyncSession`，事务原子性有保障 。
2. **事务边界明确**
   - 只在 `commit()` 时执行 `session.commit()`，异常则自动回滚，符合 UoW 的事务管理职责 。
3. **领域事件缓冲与发布**
   - 使用 `ContextVar` 存储当前 UoW，并在聚合根中通过 `register_event_from_aggregate` 收集事件，保证事件与事务一起提交后再发布 。
   - 发布时采用 Tenacity 实现重试，提升了消息投递的可靠性。
4. **清理与资源释放**
   - 在 `__aexit__` 的 `finally` 分支执行 `_cleanup()`，无论成功或失败都能关闭会话并重置 `ContextVar`，避免资源泄漏 。
5. **与 Repository 解耦**
   - 暴露了 `uow.session` 属性，由外部按需将其注入到各个 Repository，实现了写模型与 UoW 的松耦合 。

------

## 二、差异与可选改进

| 方面                     | 当前实现                                   | 建议或补充                                                   |
| ------------------------ | ------------------------------------------ | ------------------------------------------------------------ |
| **自动注入仓储**         | 无，需手动将 `uow.session` 传入各仓储      | 可在 UoW 构造时传入仓储类清单，自动实例化并挂载到 `uow.repos`（见上例） |
| **事件持久化（Outbox）** | 事件仅缓存在内存、提交后直接发布           | 若需“事务性 Outbox”，可在 `_do_commit()` 前将 `pending_events` 写入数据库 Outbox 表，再异步消费 |
| **乐观锁支持**           | 未在 UoW 层处理                            | 建议在 PO 定义 `version` 字段，并在 Repository 层 merge/flush 时捕获 `StaleDataError` |
| **异常传播与幂等**       | 发布失败后抛出，且 `pending_events` 未清空 | 可考虑在重试耗尽后，将未发布事件持久化到 Outbox 再清空内存缓冲，避免上下文泄漏 |
| **回滚事件收集**         | 回滚时仅 rollback、cleanup                 | 可在 rollback 后清空 `pending_events`，确保下次 UoW 不复用旧事件 |

------

## 三、示例：自动注入多仓储

如果你希望在 UoW 内统一管理多个仓储，可以参考如下改造思路：

```python
class SqlAlchemyAsyncUoWWithRepos(SqlAlchemyAsyncUoW):
    def __init__(self, sf, bus, repo_map: dict[str, Type]):
        super().__init__(sf, bus)
        self._repo_map = repo_map  # e.g. {"order": OrderRepository, ...}

    async def __aenter__(self):
        await super().__aenter__()
        # 批量实例化并挂到 uow.repos
        self.repos = {
            name: repo_cls(self.session)
            for name, repo_cls in self._repo_map.items()
        }
        return self
```

这样，在业务层就能通过 `uow.repos["order"]`、`uow.repos["customer"]` 直接拿到对应仓储。

------

## 四、后续讨论

- 你是否需要将事件先写入数据库 Outbox，再由独立进程消费？
- 是否在 Repository 层已经实现了乐观锁（`version` 字段）和冲突重试？
- 对自动注入仓储的方式是否有偏好，或者希望保留手动注入以便更灵活？

如果有其他细节或进一步需求，欢迎继续讨论！