"""Route Plan 状态机

定义路线计划的状态转换规则。
"""
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from idp.framework.domain.service.base import DomainService
from idp.framework.examples.domain.vo.route_plan_status import RoutePlanStatus

if TYPE_CHECKING:
    from idp.framework.examples.domain.aggregate.route_plan import RoutePlan


class RoutePlanStateMachine(DomainService):
    """路线计划状态机"""

    def __init__(self, initial_state: str = RoutePlanStatus.DRAFT):
        """初始化状态机

        Args:
            initial_state: 初始状态
        """
        self._state = initial_state

    @property
    def state(self) -> str:
        """获取当前状态"""
        return self._state

    async def trigger(self, trigger: str, stops: List[str] = None, **kwargs) -> bool:
        """触发状态转换

        Args:
            trigger: 触发器名称
            stops: 站点列表
            **kwargs: 额外参数

        Returns:
            bool: 是否成功转换状态
        """
        new_state = await self._get_next_state(trigger, stops, **kwargs)
        if new_state:
            self._state = new_state
            return True
        return False

    async def _get_next_state(self, trigger: str, stops: List[str] = None, **kwargs) -> Optional[str]:
        """获取下一个状态

        Args:
            trigger: 触发器名称
            stops: 站点列表
            **kwargs: 额外参数

        Returns:
            Optional[str]: 下一个状态，如果转换无效则返回None
        """
        # 定义状态转换规则
        transitions = {
            # 初始状态转换
            RoutePlanStatus.DRAFT: {
                "submit_for_review": RoutePlanStatus.PENDING_REVIEW,
                "cancel": RoutePlanStatus.CANCELLED
            },
            # 审核状态转换
            RoutePlanStatus.PENDING_REVIEW: {
                "approve": RoutePlanStatus.APPROVED,
                "reject": RoutePlanStatus.REJECTED,
                "cancel": RoutePlanStatus.CANCELLED
            },
            RoutePlanStatus.REJECTED: {
                "submit_for_review": RoutePlanStatus.PENDING_REVIEW,
                "cancel": RoutePlanStatus.CANCELLED
            },
            # 规划状态转换
            RoutePlanStatus.APPROVED: {
                "start_planning": RoutePlanStatus.PLANNING,
                "cancel": RoutePlanStatus.CANCELLED
            },
            RoutePlanStatus.PLANNING: {
                "complete_planning": RoutePlanStatus.PLANNED,
                "cancel": RoutePlanStatus.CANCELLED
            },
            RoutePlanStatus.PLANNED: {
                "mark_ready": RoutePlanStatus.READY,
                "cancel": RoutePlanStatus.CANCELLED
            },
            # 执行状态转换
            RoutePlanStatus.READY: {
                "dispatch": RoutePlanStatus.IN_PROGRESS,
                "cancel": RoutePlanStatus.CANCELLED
            },
            RoutePlanStatus.IN_PROGRESS: {
                "complete": RoutePlanStatus.COMPLETED,
                "fail": RoutePlanStatus.FAILED,
                "pause": RoutePlanStatus.PAUSED,
                "cancel": RoutePlanStatus.CANCELLED
            },
            RoutePlanStatus.PAUSED: {
                "resume": RoutePlanStatus.IN_PROGRESS,
                "cancel": RoutePlanStatus.CANCELLED
            },
            # 完成状态转换
            RoutePlanStatus.COMPLETED: {
                "archive": RoutePlanStatus.ARCHIVED
            },
            RoutePlanStatus.FAILED: {
                "archive": RoutePlanStatus.ARCHIVED
            },
            RoutePlanStatus.CANCELLED: {
                "archive": RoutePlanStatus.ARCHIVED
            }
        }

        # 获取当前状态允许的转换
        current_transitions = transitions.get(self._state, {})
        if trigger not in current_transitions:
            raise ValueError(
                f"Invalid transition: {trigger} from state {self._state}")

        # 检查转换条件
        if not await self._check_transition_conditions(trigger, stops, **kwargs):
            return None

        return current_transitions[trigger]

    async def _check_transition_conditions(self, trigger: str, stops: List[str] = None, **kwargs) -> bool:
        """检查状态转换条件

        Args:
            trigger: 触发器名称
            stops: 站点列表
            **kwargs: 额外参数

        Returns:
            bool: 是否满足转换条件
        """
        # 检查必填参数
        if trigger in ["reject", "cancel"] and not kwargs.get("reason"):
            raise ValueError(f"Reason is required for {trigger} transition")

        # 检查业务规则
        if trigger == "submit_for_review" and (not stops or len(stops) == 0):
            raise ValueError("Cannot submit empty route plan for review")

        if trigger == "complete_planning" and (not stops or len(stops) == 0):
            raise ValueError("Cannot complete planning without stops")

        if trigger == "dispatch" and not kwargs.get("driver"):
            raise ValueError("Driver is required for dispatch")

        return True
