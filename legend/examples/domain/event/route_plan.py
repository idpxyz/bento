"""Route Plan 领域事件

定义路线计划相关的领域事件。
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict

from idp.framework.domain.base.event import DomainEvent
from idp.framework.examples.domain.vo.route_plan_status import RoutePlanStatus


class RoutePlanCreated(DomainEvent):
    """路线计划创建事件"""
    plan_id: str
    stops: List[str]
    tenant_id: Optional[str] = None

    model_config = ConfigDict(frozen=True)


class RoutePlanStatusChanged(DomainEvent):
    """路线计划状态变更事件"""
    plan_id: str
    tenant_id: Optional[str] = None
    old_status: str
    new_status: str
    reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(frozen=True)

    @property
    def is_created(self) -> bool:
        """是否是创建状态"""
        return self.new_status == RoutePlanStatus.DRAFT

    @property
    def is_dispatched(self) -> bool:
        """是否是派发状态"""
        return self.new_status == RoutePlanStatus.IN_PROGRESS

    @property
    def is_completed(self) -> bool:
        """是否是完成状态"""
        return self.new_status == RoutePlanStatus.COMPLETED

    @property
    def is_cancelled(self) -> bool:
        """是否是取消状态"""
        return self.new_status == RoutePlanStatus.CANCELLED

    @property
    def is_failed(self) -> bool:
        """是否是失败状态"""
        return self.new_status == RoutePlanStatus.FAILED

    @property
    def is_archived(self) -> bool:
        """是否是归档状态"""
        return self.new_status == RoutePlanStatus.ARCHIVED
