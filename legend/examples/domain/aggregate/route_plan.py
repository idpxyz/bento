"""Route Plan 聚合根

表示一个完整的路线计划，包含多个站点。
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from idp.framework.domain.base import BaseAggregateRoot
from idp.framework.examples.domain.event.route_plan import (
    RoutePlanCreated,
    RoutePlanStatusChanged,
)
from idp.framework.examples.domain.service.route_plan_state import RoutePlanStateMachine
from idp.framework.examples.domain.vo.route_plan_status import RoutePlanStatus
from idp.framework.infrastructure.persistence.sqlalchemy.uow import (
    register_event_from_aggregate,
)


class RoutePlan(BaseAggregateRoot):
    """路线计划聚合根

    表示一个完整的路线计划，包含多个站点。"""

    def __init__(
        self,
        stops: List[str],
        tenant_id: Optional[str] = None,
        id: Optional[str] = None,
        status: str = RoutePlanStatus.DRAFT,
        name: str = "",
        description: Optional[str] = None,
        is_active: bool = True,
        register_event: bool = True,
    ):
        """初始化路线计划

        Args:
            stops: 站点ID列表
            tenant_id: 租户ID
            id: 路线计划ID，如果不提供则自动生成
            status: 路线计划状态
            name: 路线计划名称
            description: 路线计划描述
            is_active: 是否启用
        """
        super().__init__(id=id or str(uuid.uuid4()))
        self._stops = stops
        self._tenant_id = tenant_id
        self._name = name
        self._description = description
        self._is_active = is_active

        # 初始化状态机
        self._state_machine = RoutePlanStateMachine(initial_state=status)

        # 触发创建事件
        if register_event:
            register_event_from_aggregate(
                RoutePlanCreated(
                    plan_id=str(self.id),
                tenant_id=self._tenant_id,
                stops=self._stops,
                )
            )

        # 如果不是初始状态，触发状态变更事件
        if status != RoutePlanStatus.DRAFT:
            register_event_from_aggregate(
                RoutePlanStatusChanged(
                    plan_id=str(self.id),
                    tenant_id=self._tenant_id,
                    old_status=RoutePlanStatus.DRAFT,
                    new_status=status,
                    reason="Initial state",
                )
            )

    @property
    def stops(self) -> List[str]:
        """获取站点ID列表"""
        return self._stops

    @property
    def status(self) -> str:
        """获取路线计划状态"""
        return self._state_machine.state

    @property
    def tenant_id(self) -> Optional[str]:
        """获取租户ID"""
        return self._tenant_id

    @property
    def name(self) -> str:
        """获取路线计划名称"""
        return self._name

    @property
    def description(self) -> Optional[str]:
        """获取路线计划描述"""
        return self._description

    @property
    def is_active(self) -> bool:
        """获取是否启用"""
        return self._is_active

    def update_stops(self, stops: List[str]) -> None:
        """更新站点列表

        Args:
            stops: 新的站点ID列表
        """
        self._stops = stops

    def update_tenant_id(self, tenant_id: Optional[str]) -> None:
        """更新租户ID

        Args:
            tenant_id: 新的租户ID
        """
        self._tenant_id = tenant_id

    async def change_status(self, trigger: str, **kwargs) -> None:
        """统一的状态转换方法

        Args:
            trigger: 状态转换触发器名称
            **kwargs: 状态转换的额外参数
        """
        old_status = self.status
        success = await self._state_machine.trigger(trigger, stops=self._stops, **kwargs)
        if success:
            # 触发状态变更事件
            register_event_from_aggregate(
                RoutePlanStatusChanged(
                    plan_id=str(self.id),
                    tenant_id=self._tenant_id,
                    old_status=old_status,
                    new_status=self.status,
                    reason=kwargs.get('reason'),
                    metadata=kwargs.get('metadata')
                )
            )

    # 业务语义方法 - 这些方法内部调用 change_status
    async def submit_for_review(self, reason: Optional[str] = None) -> None:
        """提交审核

        Args:
            reason: 提交原因
        """
        await self.change_status('submit_for_review', reason=reason)

    async def approve(self, reason: Optional[str] = None) -> None:
        """审核通过

        Args:
            reason: 审核通过原因
        """
        await self.change_status('approve', reason=reason)

    async def reject(self, reason: str) -> None:
        """审核拒绝

        Args:
            reason: 拒绝原因
        """
        await self.change_status('reject', reason=reason)

    async def revise(self, reason: Optional[str] = None) -> None:
        """修改后重新提交

        Args:
            reason: 修改原因
        """
        await self.change_status('revise', reason=reason)

    async def start_planning(self, reason: Optional[str] = None) -> None:
        """开始规划

        Args:
            reason: 开始规划原因
        """
        await self.change_status('start_planning', reason=reason)

    async def complete_planning(self, reason: Optional[str] = None) -> None:
        """完成规划

        Args:
            reason: 完成规划原因
        """
        await self.change_status('complete_planning', reason=reason)

    async def mark_ready(self, reason: Optional[str] = None) -> None:
        """标记就绪

        Args:
            reason: 就绪原因
        """
        await self.change_status('mark_ready', reason=reason)

    async def start_execution(self, reason: Optional[str] = None) -> None:
        """开始执行

        Args:
            reason: 开始执行原因
        """
        await self.change_status('start_execution', reason=reason)

    async def pause(self, reason: str) -> None:
        """暂停执行

        Args:
            reason: 暂停原因
        """
        await self.change_status('pause', reason=reason)

    async def resume(self, reason: Optional[str] = None) -> None:
        """恢复执行

        Args:
            reason: 恢复原因
        """
        await self.change_status('resume', reason=reason)

    async def complete(self, reason: Optional[str] = None) -> None:
        """完成执行

        Args:
            reason: 完成原因
        """
        await self.change_status('complete', reason=reason)

    async def partially_complete(self, reason: str) -> None:
        """部分完成

        Args:
            reason: 部分完成原因
        """
        await self.change_status('partially_complete', reason=reason)

    async def fail(self, reason: str) -> None:
        """执行失败

        Args:
            reason: 失败原因
        """
        await self.change_status('fail', reason=reason)

    async def retry_planning(self, reason: str) -> None:
        """重试规划

        Args:
            reason: 重试原因
        """
        await self.change_status('retry_planning', reason=reason)

    async def complete_retry_planning(self, reason: Optional[str] = None) -> None:
        """完成重试规划

        Args:
            reason: 完成重试规划原因
        """
        await self.change_status('complete_retry_planning', reason=reason)

    async def start_retry(self, reason: Optional[str] = None) -> None:
        """开始重试执行

        Args:
            reason: 开始重试原因
        """
        await self.change_status('start_retry', reason=reason)

    async def archive(self, reason: Optional[str] = None) -> None:
        """归档

        Args:
            reason: 归档原因
        """
        await self.change_status('archive', reason=reason)

    async def cancel(self, reason: str) -> None:
        """取消路线计划

        Args:
            reason: 取消原因
        """
        await self.change_status('cancel', reason=reason)
