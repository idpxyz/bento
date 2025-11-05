# ──────────────────────  domain/model/route_plan.py  ──────────────────────
"""Route Plan 聚合根 – 最小可运行版本
* 在 DDD 实践里，聚合方法保持同步是业界常态。
* 领域事件：`RoutePlanCreated`, `RoutePlanDispatched`
* 行为：`dispatch()` 由 READY → IN_PROGRESS
* 示例字段：`id`, `stops`, `status`, `created_at`

此文件只依赖 `AggregateRoot` 与 `DomainEvent` 基类，位于
`idp/domain/model/route_plan.py`。后续会有对应 Repository + PO。"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from idp.framework.domain.base.entity import AggregateRoot
from idp.framework.examples.domain.event.route_plan import (
    RoutePlanCancelled,
    RoutePlanCompleted,
    RoutePlanCreated,
    RoutePlanDispatched,
)

__all__ = ["RoutePlan", "RoutePlanStatus", "RoutePlanDTO"]

# ------------------------------ 状态枚举 -----------------------------


class RoutePlanStatus:
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    CANCELLED = "CANCELLED"

# ----------------------------- 聚合根 ------------------------------


class RoutePlan(AggregateRoot):
    """路线计划聚合根

    表示一个完整的路线计划，包含多个站点。"""

    def __init__(
        self,
        stops: List[str],
        tenant_id: Optional[str] = None,
        id: Optional[str] = None,
        status: Optional[str] = None,
        **kwargs
    ):
        """初始化路线计划

        Args:
            stops: 站点列表
            tenant_id: 租户ID，可选
            id: 路线计划ID，可选，如果不提供则自动生成
            status: 路线计划状态，可选，默认为 READY
            **kwargs: 其他参数
        """
        # 生成或使用提供的ID
        if id is None:
            id = str(uuid.uuid4())
        super().__init__(id=id, **kwargs)

        self._stops = stops
        self._tenant_id = tenant_id
        self._set_status(status or RoutePlanStatus.READY)

        # 触发领域事件
        self.raise_event(
            RoutePlanCreated(
                aggregate_id=str(self.id),
                tenant_id=self._tenant_id,
                stops=self._stops,
            )
        )

    @property
    def stops(self) -> List[str]:
        """获取站点列表"""
        return self._stops

    @property
    def status(self) -> str:
        """获取路线计划状态"""
        return self._status

    @property
    def tenant_id(self) -> Optional[str]:
        """获取租户ID"""
        return self._tenant_id

    def _set_status(self, new_status: str) -> None:
        """内部方法：设置路线计划状态

        这个方法主要用于从持久化对象恢复领域对象时使用。
        正常的状态变更应该使用 update_status() 方法。

        Args:
            new_status: 新状态
        """
        self._status = new_status

    def update_status(self, new_status: str) -> None:
        """更新路线计划状态

        Args:
            new_status: 新状态
        """
        self._set_status(new_status)
        self.add_domain_event("RoutePlanStatusChanged", {
            "route_plan_id": str(self.id),
            "old_status": self._status,
            "new_status": new_status
        })

    def add_stop(self, stop: str) -> None:
        """添加站点

        Args:
            stop: 站点ID
        """
        if stop not in self._stops:
            self._stops.append(stop)
            self.add_domain_event("StopAddedToRoutePlan", {
                "route_plan_id": str(self.id),
                "stop_id": stop
            })

    def remove_stop(self, stop: str) -> None:
        """移除站点

        Args:
            stop: 站点ID
        """
        if stop in self._stops:
            self._stops.remove(stop)
            self.add_domain_event("StopRemovedFromRoutePlan", {
                "route_plan_id": str(self.id),
                "stop_id": stop
            })

    # ------------------------ 行为方法 --------------------------
    def dispatch(self, driver: str) -> None:
        if self._status != RoutePlanStatus.READY:
            raise ValueError("RoutePlan already dispatched or completed")
        self._set_status(RoutePlanStatus.IN_PROGRESS)
        self.raise_event(
            RoutePlanDispatched(
                aggregate_id=str(self.id),
                tenant_id=self._tenant_id,
                driver=driver,
            )
        )

    def complete(self) -> None:
        if self._status != RoutePlanStatus.IN_PROGRESS:
            raise ValueError("RoutePlan not in progress")
        self._set_status(RoutePlanStatus.DONE)
        self.raise_event(
            RoutePlanCompleted(
                aggregate_id=str(self.id),
                tenant_id=self._tenant_id,
            )
        )

    def cancel(self) -> None:
        if self._status in [RoutePlanStatus.DONE, RoutePlanStatus.CANCELLED]:
            raise ValueError("RoutePlan already completed or cancelled")
        self._set_status(RoutePlanStatus.CANCELLED)
        self.raise_event(
            RoutePlanCancelled(
                aggregate_id=str(self.id),
                tenant_id=self._tenant_id,
            )
        )

# ───────────────────────────── End of file ─────────────────────────────
