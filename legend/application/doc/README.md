### `service/` vs `process/` —— 站位与职责

| 层级                                                         | 典型内容                                                                          | 触点                                        | 一致性                       | 命名含义                          |
| ---------------------------------------------------------- | ----------------------------------------------------------------------------- | ----------------------------------------- | ------------------------- | ----------------------------- |
| **service/**<br>（Application Service / Transaction Script） | *单* UoW 内就能完成的用例：<br> • 校验参数<br> • 调用 1–2 个聚合方法<br> • 写同一 DB、同一 Outbox        | - REST/GraphQL   - CLI<br>调用者希望**立即得到结果** | **强事务**<br>ACID 覆盖全部步骤    | “把多个 domain 调用**组合成一次事务**的服务” |
| **process/**<br>（Process Manager / Saga Orchestrator）      | 跨聚合、跨上下文甚至跨服务的**长业务流程**：<br> • 监听领域/集成事件<br> • 协调多条 Command<br> • 维护 Saga 状态表 | 事件总线<br>偶尔暴露 *command → start saga* 的 API | **最终一致**<br>写多库、多服务；失败需补偿 | “持续**编排**，直到流程结束”             |

> **一句话**：
> *service* = 同库/同事务的“短脚本”；
> *process* = 跨库/跨服务、长生命周期的“编排器”。

---

## 什么时候还需要 `service/` 目录？

| 场景             | 说明                                                                                |
| -------------- | --------------------------------------------------------------------------------- |
| **单一聚合但步骤很多**  | 例如 *ReplenishmentService*：虽然要查库存、选库位、下补货单，但它们仍在同一数据库事务里完成 + 立即返回业务结果。             |
| **简化 Handler** | 若你用 CQRS，但某些 Command 需要①权限校验②参数清洗③调用聚合——把这些前置逻辑放在 Service，比把所有代码塞进 Handler 可读性更好。 |
| **多个聚合但仍可强一致** | 比如 Inventory + Location 共享同一库，可在一个 UoW 里完成；不必引入 Saga。                             |
| **非公开的“内部用例”** | 供 Batch/Scheduler 调用的脚本（月底结算、同步主数据）。                                              |

## 什么时候可以删掉 `service/`？

* 当所有写操作都已经**严格遵循 CQRS Command/Handler**且 Handler 很薄；
* 或者你根本采用 *Rich Domain Model + Thin Application Layer*，只有聚合方法，没有额外用例脚本。

---

## 两目录并存的推荐做法

```
application/
├── command/                 # 写端
│   └── *.py
├── query/                   # 读端
│   └── *.py
├── service/                 # 强事务脚本
│   └── replenishment_service.py
└── process/                 # Saga / 长流程
    ├── dispatch_process.py
    └── replenishment_pm.py
```

1. **Handler → Service → Domain**
   写端 Handler 如果逻辑简单可直调聚合；复杂就调 `service/`。
2. **Process 只监听事件**
   不暴露 REST；用状态表/Saga ID 驱动补偿 & 冪等。
3. **方便渐进拆分**
   以后把某条用例拆成 Saga，只需把代码从 `service/` 挪到 `process/` 并改为事件驱动即可。

---

### 结论

* 二者关注点不同：
  **service** = *一次事务内* 的“应用用例脚本”；
  **process** = *跨事务*、需补偿/重试的“长流程编排”。
* 在大型系统中 **两者都有存在价值**。只有当你的 Handler 足够薄、所有跨聚合协作都已 Saga 化时，才可以精简掉 `service/` 目录。




### 把 `WarehouseFacade` 放到哪？

**最合适的位置： `application/service/warehouse_facade.py`**
理由：

| 判断维度        | `WarehouseFacade.merge_warehouse()` 特征      | 映射到目录               |
| ----------- | ------------------------------------------- | ------------------- |
| **事务边界**    | 查询 → 发两个命令，全程希望*一次 HTTP 调用即可完成*；不跨库、不等待异步事件 | **Service**（强一致脚本）  |
| **时长 / 状态** | 没有长生命周期、补偿、状态机；执行完就结束                       | 不是 *Process/Saga*   |
| **依赖模式**    | 注入 `CommandBus`、`QueryService`，同步调用         | Application Service |
| **上下文**     | 只处理 *Warehouse* 子领域内部逻辑                     | 不需要跨上下文编排           |

> 如果将来需要把 “合并仓库” 拆成长流程（审批、异步通知、补偿回滚），再把逻辑迁到 `application/process/merge_warehouse_pm.py` 并改为事件驱动。

---

## 建议的文件结构

```
application/
├── command/
│   ├── merge_warehouse_cmd.py          # MergeWarehouseCommand & handler
│   └── delete_warehouse_cmd.py
├── query/
│   └── warehouse_query_service.py      # WarehouseQueryService
└── service/
    └── warehouse_facade.py             # ← 放置这里
```

### `warehouse_facade.py`

```python
# application/service/warehouse_facade.py
from __future__ import annotations
from uuid import UUID
from idp.application.command.merge_warehouse_cmd import MergeWarehouseCommand
from idp.application.command.delete_warehouse_cmd import DeleteWarehouseCommand
from idp.application.query.warehouse_query_service import WarehouseQueryService
from idp.infrastructure.messaging.core.command_bus import CommandBus

class WarehouseFacade:
    """Application-service facade that coordinates *multiple* commands."""

    def __init__(
        self,
        command_bus: CommandBus,
        query_service: WarehouseQueryService,
    ):
        self._cmd_bus = command_bus
        self._query = query_service

    async def merge_warehouse(self, source_id: UUID, target_id: UUID):
        # 1. 读模型校验存在
        if not await self._query.exists(source_id) or not await self._query.exists(target_id):
            raise ValueError("source / target warehouse not found")

        # 2. 发送“合并”命令
        await self._cmd_bus.dispatch(
            MergeWarehouseCommand(source_id=source_id, target_id=target_id)
        )

        # 3. 删除源仓库
        await self._cmd_bus.dispatch(DeleteWarehouseCommand(id=source_id))
```

---

## 何时迁到 `process/`？

| 条件                                | 动作                                                                                                                 |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| 合并仓库需要 **审批流程**、**异步通知**、**补偿回滚** | 新建 `application/process/merge_warehouse_pm.py` 继承 ProcessManager / Saga；监听 `WarehouseMerged`、`WarehouseDeleted` 事件 |
| 跨服务（Inventory、Order）协调            | Saga 中分阶段发送外部 Command、维护状态表                                                                                        |

直到那时再把旧的 `WarehouseFacade` “薄化”为仅启动 Saga 的命令即可。

---

### 结论

* 当前 **同步、短事务** 的协调逻辑 ⇒ `application/service/`
* 保持目录与职责清晰：

  * `service/` = 强事务脚本 / facade
  * `process/` = 跨事务 Saga / 长流程 orchestrator


已在 **`application/process/merge_warehouse_pm.py`** 中放置了一个完整的 **Process-Manager/Saga** 示例：

* **MergeWarehouseSagaPO** — 持久化 Saga 状态表
* **MergeWarehouseProcessManager** — 监听事件、分步派发 `MoveBinsCommand → DeleteWarehouseCommand`，并维护状态
* **register\_merge\_warehouse\_pm()** — 启动时把 PM 订阅到 `EventBus`

这样与 `service/warehouse_facade.py` 形成互补：

* **Facade** 仍可直接用在同事务的小用例。
* **Process Manager** 处理跨上下文、需补偿的长流程。

后续可按需补充事件类 (`BinsMoved`) 或错误补偿逻辑。
