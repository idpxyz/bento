"""Route Plan 领域异常

定义路线计划相关的领域异常。
"""
from idp.framework.exception.classified import DomainException
from idp.framework.exception.metadata import ErrorCode


class RoutePlanException(DomainException):
    """路线计划异常类"""
    pass


class RouterPlanStatusErrorCode(ErrorCode):
    """路线计划状态异常"""
    ROUTE_PLAN_NOT_IN_PROGRESS = ErrorCode(
        code="route_plan_not_in_progress",
        message="路线计划不在进行中",
        http_status=400
    )
    ROUTE_PLAN_ALREADY_COMPLETED = ErrorCode(
        code="route_plan_already_completed",
        message="路线计划已经完成",
        http_status=400
    )
    ROUTE_PLAN_ALREADY_CANCELLED = ErrorCode(
        code="route_plan_already_cancelled",
        message="路线计划已经取消",
        http_status=400
    )

    ROUTE_PLAN_ALREADY_PAUSED = ErrorCode(
        code="route_plan_already_paused",
        message="路线计划已经暂停",
        http_status=400
    )

    ROUTE_PLAN_ALREADY_RESUMED = ErrorCode(
        code="route_plan_already_resumed",
        message="路线计划已经恢复",
        http_status=400
    )

    ROUTE_PLAN_ALREADY_RESTARTED = ErrorCode(
        code="route_plan_already_restarted",
        message="路线计划已经重新启动",
        http_status=400
    )

    ROUTE_PLAN_ALREADY_SUSPENDED = ErrorCode(
        code="route_plan_already_suspended",
        message="路线计划已经暂停",
        http_status=400
    )

    ROUTE_PLAN_ALREADY_RESUMED = ErrorCode(
        code="route_plan_already_resumed",
        message="路线计划已经恢复",
        http_status=400
    )
