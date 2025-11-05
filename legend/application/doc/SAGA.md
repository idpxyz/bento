### ✅ 已新增 **`application/saga/saga_manager.py`**

* **目录命名**：完全可以用 **`saga/`** 取代 `process/`，更直观表达 *Saga / Process Manager* 职责。
* **核心内容**

  1. `@saga(EventType)` 装饰器 —— 给协程方法打标签
  2. `SagaManager` 抽象基类 —— 自动扫描并把标记方法订阅到 `EventBus`
  3. `_upsert_state()` —— 统一写入 Saga 状态表
  4. **示例** `MergeWarehouseSaga`：三步完成仓库合并编排
  5. `register_sagas(bus, *classes)` —– 应用启动时批量注册

> 你只需在 FastAPI startup 中：

```python
from application.saga.saga_manager import register_sagas, MergeWarehouseSaga
register_sagas(app.state.event_bus, MergeWarehouseSaga)
```

即可让 Saga Manager 生效。
如需更多 Saga（补货、ASN 收货、跨账期结算），继承 `SagaManager` 并用 `@saga` 标注事件处理器即可。


```python
# ───────────── application/saga/saga_manager.py ─────────────
"""Generic **Saga Manager**  – event‑driven orchestrator skeleton.

*Why separate `saga/` directory?*

`process/` 与 `saga/` 可视为同义；若团队喜欢 “Saga” 一词更贴近
模式语义（长事务 + 补偿），可以把所有编排器放在 `application/saga/`。

此文件提供一个 **可复用基类 `SagaManager`** 与 `@saga` decorator，帮助你：
• 定义 Saga 状态表 (SQLAlchemy PO)
• 自动路由事件到对应协程处理器
• 提供 `register_sagas(event_bus)` 批量注册
"""

from __future__ import annotations

import asyncio, logging, inspect
from abc import ABC
from functools import wraps
from typing import Any, Awaitable, Callable, Dict, Type
from uuid import UUID, uuid4
from datetime import datetime

from sqlalchemy.orm import mapped_column, Mapped, DeclarativeBase
from sqlalchemy.dialects.postgresql import UUID as pgUUID, VARCHAR, JSONB, TIMESTAMP

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SQLAlchemy base for saga state tables (can be shared across managers)
# ---------------------------------------------------------------------------
class SagaBase(DeclarativeBase):
    pass

# ---------------------------------------------------------------------------
# Saga decorator to mark handler methods
# ---------------------------------------------------------------------------
Handler = Callable[[Any], Awaitable[None]]


def saga(event_type: Type[Any]):
    """Decorator: mark a method as handler for *event_type* inside a SagaManager."""

    def _decorator(func: Handler):
        setattr(func, "_saga_evt", event_type)
        return func

    return _decorator

# ---------------------------------------------------------------------------
# Generic SagaManager
# ---------------------------------------------------------------------------
class SagaManager(ABC):
    """Base‑class for saga orchestrators.

    Sub‑class must:
    • provide `uow` (async Unit‑of‑Work)
    • declare async methods decorated with `@saga(EventType)`
    • optionally define inner State PO (inherits SagaBase)
    """

    # you may inject these via DI / __init__
    uow: Any           # SqlAlchemyAsyncUoW
    cmd_bus: Any       # CommandBus

    # -------------- helpers --------------
    async def _upsert_state(self, saga_id: UUID, **kwargs):
        """Insert or update saga state row (simple key/value JSON)."""
        async with self.uow:
            session = self.uow._session
            from sqlalchemy import select, update, insert

            tbl = self.State  # type: ignore[attr-defined]
            stmt = select(tbl).where(tbl.saga_id == saga_id)
            row = (await session.scalars(stmt)).first()
            if row:
                await session.execute(update(tbl).where(tbl.saga_id == saga_id).values(**kwargs))
            else:
                data = {**kwargs, "saga_id": saga_id}
                await session.execute(insert(tbl).values(**data))

    # -------------- registration ----------
    @classmethod
    def register(cls, bus):
        """Scan methods with `@saga` and subscribe them to EventBus."""
        instance = cls()  # assume DI container would inject deps
        for _, m in inspect.getmembers(instance, predicate=inspect.iscoroutinefunction):
            evt = getattr(m, "_saga_evt", None)
            if evt is not None:
                bus.subscribe(evt, m)
                logger.info("Saga %s subscribed to %s", cls.__name__, evt.__name__)
        return instance

# ---------------------------------------------------------------------------
# Example concrete saga table + manager
# ---------------------------------------------------------------------------
class MergeWarehouseState(SagaBase):
    __tablename__ = "merge_warehouse_saga"

    saga_id: Mapped[UUID] = mapped_column(pgUUID(as_uuid=True), primary_key=True, default=uuid4)
    source_id: Mapped[UUID] = mapped_column(pgUUID(as_uuid=True))
    target_id: Mapped[UUID] = mapped_column(pgUUID(as_uuid=True))
    step: Mapped[str] = mapped_column(VARCHAR(32))
    meta: Mapped[dict] = mapped_column(JSONB, default=dict)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


# imagine these events exist in domain package
class MergeWarehouseRequested: ...
class BinsMoved: ...
class WarehouseDeleted: ...


class MergeWarehouseSaga(SagaManager):
    """Concrete saga orchestrating Merge‑Warehouse across contexts."""

    State = MergeWarehouseState  # attach table class

    # uow / cmd_bus will be injected by your DI framework
    def __init__(self, uow=None, cmd_bus=None):
        self.uow = uow
        self.cmd_bus = cmd_bus

    # ── step‑1 ────────────────────────────────────────────
    @saga(MergeWarehouseRequested)
    async def on_request(self, evt: MergeWarehouseRequested):
        saga_id = uuid4()
        await self._upsert_state(saga_id, source_id=evt.source_id, target_id=evt.target_id, step="move_bins")
        await self.cmd_bus.dispatch({"type": "MoveBins", "saga_id": str(saga_id), "source": str(evt.source_id), "target": str(evt.target_id)})

    # ── step‑2 ────────────────────────────────────────────
    @saga(BinsMoved)
    async def on_bins_moved(self, evt: BinsMoved):
        await self._upsert_state(evt.saga_id, step="delete_source")
        await self.cmd_bus.dispatch({"type": "DeleteWarehouse", "id": str(evt.source_id), "saga_id": str(evt.saga_id)})

    # ── step‑3 ────────────────────────────────────────────
    @saga(WarehouseDeleted)
    async def on_deleted(self, evt: WarehouseDeleted):
        await self._upsert_state(evt.saga_id, step="DONE")
        logger.info("MergeWarehouseSaga %s completed", evt.saga_id)

# ------------------ utility for startup ------------------

def register_sagas(bus, *saga_classes: Type[SagaManager]):
    """Call once during FastAPI/worker startup to register all sagas."""
    instances = [cls.register(bus) for cls in saga_classes]
    return instances

# ───────────────────────── End of file ─────────────────────────
```