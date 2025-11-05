"""路线计划API路由

定义路线计划的API路由。
"""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from idp.framework.examples.api.schema.route_plan import (
    CreateRoutePlanRequest,
    CreateRoutePlanResponse,
    OperationResponse,
    RoutePlanResponse,
    StopResponse,
    UpdateRoutePlanRequest,
)
from idp.framework.examples.application.command.route_plan import (
    ChangeRoutePlanStatusCommand,
    CreateRoutePlanCommand,
    UpdateRoutePlanCommand,
)
from idp.framework.examples.application.command_handler.route_plan import (
    ChangeRoutePlanStatusHandler,
    CreateRoutePlanHandler,
    UpdateRoutePlanHandler,
)
from idp.framework.examples.application.di.route_plan import (
    get_route_plan_repository,
    get_uow,
)
from idp.framework.examples.application.query.route_plan import (
    GetRoutePlanHandler,
    GetRoutePlanQuery,
    ListRoutePlansHandler,
    ListRoutePlansQuery,
)
from idp.framework.examples.domain.repository.route_plan import (
    AbstractRoutePlanRepository,
)
from idp.framework.examples.infrastructure.persistence.po.stop import StopPO

router = APIRouter(prefix="/route-plans", tags=["route-plans"])


@router.post("", response_model=CreateRoutePlanResponse)
async def create_route_plan(
    request: CreateRoutePlanRequest,
    uow=Depends(get_uow)
) -> CreateRoutePlanResponse:
    """创建路线计划

    Args:
        request: 创建路线计划请求
        uow: 工作单元

    Returns:
        CreateRoutePlanResponse: 创建路线计划响应
    """
    handler = CreateRoutePlanHandler(uow)
    plan_id = await handler.handle(CreateRoutePlanCommand(
        stops=request.stops,
        tenant_id=request.tenant_id
    ))
    return CreateRoutePlanResponse(id=plan_id)


@router.get("/{plan_id}", response_model=RoutePlanResponse)
async def get_route_plan(
    plan_id: UUID,
    route_plan_repository=Depends(get_route_plan_repository)
) -> RoutePlanResponse:
    """获取路线计划

    Args:
        plan_id: 路线计划ID
        route_plan_repository: 路线计划仓储

    Returns:
        RoutePlanResponse: 路线计划响应

    Raises:
        HTTPException: 如果路线计划不存在
    """
    handler = GetRoutePlanHandler(route_plan_repository)
    route_plan = await handler.handle(GetRoutePlanQuery(plan_id=plan_id))
    if not route_plan:
        raise HTTPException(
            status_code=404, detail=f"Route plan with id {plan_id} not found")

    # 获取完整的站点信息
    stops = []
    for stop_id in route_plan.stops:
        stop = await route_plan_repository._uow.session.get(StopPO, stop_id)
        if stop:
            # 将 StopPO 转换为 StopResponse
            location = None
            if stop.latitude is not None and stop.longitude is not None:
                location = {
                    "latitude": stop.latitude,
                    "longitude": stop.longitude
                }

            contact = None
            if stop.contact_name and stop.contact_phone and stop.contact_email:
                contact = {
                    "name": stop.contact_name,
                    "phone": stop.contact_phone,
                    "email": stop.contact_email
                }

            stop_response = StopResponse(
                id=stop.id,
                name=stop.name,
                address=stop.address,
                location=location,
                contact=contact,
                description=stop.description,
                is_active=stop.is_active,
                tenant_id=stop.tenant_id
            )
            stops.append(stop_response)

    return RoutePlanResponse(
        id=route_plan.id,
        stops=stops,
        status=route_plan.status,
        tenant_id=route_plan.tenant_id
    )


@router.get("", response_model=List[RoutePlanResponse])
async def list_route_plans(
    status: str | None = None,
    tenant_id: str | None = None,
    route_plan_repository=Depends(get_route_plan_repository)
) -> List[RoutePlanResponse]:
    """列出路线计划

    Args:
        status: 路线计划状态
        tenant_id: 租户ID
        route_plan_repository: 路线计划仓储

    Returns:
        List[RoutePlanResponse]: 路线计划响应列表
    """
    handler = ListRoutePlansHandler(route_plan_repository)
    route_plans = await handler.handle(ListRoutePlansQuery(
        status=status,
        tenant_id=tenant_id
    ))

    result = []
    for route_plan in route_plans:
        # 获取完整的站点信息
        stops = []
        for stop_id in route_plan.stops:
            stop = await route_plan_repository._uow.session.get(StopPO, stop_id)
            if stop:
                # 将 StopPO 转换为 StopResponse
                location = None
                if stop.latitude is not None and stop.longitude is not None:
                    location = {
                        "latitude": stop.latitude,
                        "longitude": stop.longitude
                    }

                contact = None
                if stop.contact_name and stop.contact_phone and stop.contact_email:
                    contact = {
                        "name": stop.contact_name,
                        "phone": stop.contact_phone,
                        "email": stop.contact_email
                    }

                stop_response = StopResponse(
                    id=stop.id,
                    name=stop.name,
                    address=stop.address,
                    location=location,
                    contact=contact,
                    description=stop.description,
                    is_active=stop.is_active,
                    tenant_id=stop.tenant_id
                )
                stops.append(stop_response)

        result.append(RoutePlanResponse(
            id=route_plan.id,
            stops=stops,
            status=route_plan.status,
            tenant_id=route_plan.tenant_id
        ))

    return result


@router.put("/{plan_id}", response_model=OperationResponse)
async def update_route_plan(
    plan_id: UUID,
    request: UpdateRoutePlanRequest,
    uow=Depends(get_uow)
) -> OperationResponse:
    """更新路线计划

    Args:
        plan_id: 路线计划ID
        request: 更新路线计划请求
        uow: 工作单元

    Returns:
        OperationResponse: 操作响应
    """
    handler = UpdateRoutePlanHandler(uow)
    await handler.handle(UpdateRoutePlanCommand(
        id=str(plan_id),
        stops=request.stops,
        tenant_id=request.tenant_id
    ))
    return OperationResponse(
        success=True,
        message="路线计划更新成功"
    )


@router.post("/{plan_id}/submit-for-review", response_model=OperationResponse)
async def submit_for_review(
    plan_id: UUID,
    route_plan_repository: AbstractRoutePlanRepository = Depends(
        get_route_plan_repository)
) -> OperationResponse:
    """提交审核

    Args:
        plan_id: 路线计划ID
        route_plan_repository: 路线计划仓储

    Returns:
        OperationResponse: 操作响应
    """
    route_plan = await route_plan_repository.get_by_id(str(plan_id))
    if not route_plan:
        raise HTTPException(
            status_code=404, detail=f"Route plan with id {plan_id} not found")

    handler = ChangeRoutePlanStatusHandler(route_plan_repository._uow)
    await handler.handle(ChangeRoutePlanStatusCommand(
        id=str(plan_id),
        trigger="submit_for_review"
    ))
    return OperationResponse(
        success=True,
        message="路线计划已提交审核"
    )


@router.post("/{plan_id}/approve", response_model=OperationResponse)
async def approve(
    plan_id: UUID,
    route_plan_repository: AbstractRoutePlanRepository = Depends(
        get_route_plan_repository)
) -> OperationResponse:
    """审核通过

    Args:
        plan_id: 路线计划ID
        route_plan_repository: 路线计划仓储

    Returns:
        OperationResponse: 操作响应
    """
    route_plan = await route_plan_repository.get_by_id(str(plan_id))
    if not route_plan:
        raise HTTPException(
            status_code=404, detail=f"Route plan with id {plan_id} not found")

    handler = ChangeRoutePlanStatusHandler(route_plan_repository._uow)
    await handler.handle(ChangeRoutePlanStatusCommand(
        id=str(plan_id),
        trigger="approve"
    ))
    return OperationResponse(
        success=True,
        message="路线计划已审核通过"
    )


@router.post("/{plan_id}/reject", response_model=OperationResponse)
async def reject(
    plan_id: UUID,
    route_plan_repository: AbstractRoutePlanRepository = Depends(
        get_route_plan_repository)
) -> OperationResponse:
    """审核拒绝

    Args:
        plan_id: 路线计划ID
        route_plan_repository: 路线计划仓储

    Returns:
        OperationResponse: 操作响应
    """
    route_plan = await route_plan_repository.get_by_id(str(plan_id))
    if not route_plan:
        raise HTTPException(
            status_code=404, detail=f"Route plan with id {plan_id} not found")

    handler = ChangeRoutePlanStatusHandler(route_plan_repository._uow)
    await handler.handle(ChangeRoutePlanStatusCommand(
        id=str(plan_id),
        trigger="reject",
        reason="审核未通过"
    ))
    return OperationResponse(
        success=True,
        message="路线计划已拒绝"
    )


@router.post("/{plan_id}/start-planning", response_model=OperationResponse)
async def start_planning(
    plan_id: UUID,
    route_plan_repository: AbstractRoutePlanRepository = Depends(
        get_route_plan_repository)
) -> OperationResponse:
    """开始规划

    Args:
        plan_id: 路线计划ID
        route_plan_repository: 路线计划仓储

    Returns:
        OperationResponse: 操作响应
    """
    route_plan = await route_plan_repository.get_by_id(str(plan_id))
    if not route_plan:
        raise HTTPException(
            status_code=404, detail=f"Route plan with id {plan_id} not found")

    handler = ChangeRoutePlanStatusHandler(route_plan_repository._uow)
    await handler.handle(ChangeRoutePlanStatusCommand(
        id=str(plan_id),
        trigger="start_planning"
    ))
    return OperationResponse(
        success=True,
        message="路线计划开始规划"
    )


@router.post("/{plan_id}/complete-planning", response_model=OperationResponse)
async def complete_planning(
    plan_id: UUID,
    route_plan_repository: AbstractRoutePlanRepository = Depends(
        get_route_plan_repository)
) -> OperationResponse:
    """完成规划

    Args:
        plan_id: 路线计划ID
        route_plan_repository: 路线计划仓储

    Returns:
        OperationResponse: 操作响应
    """
    route_plan = await route_plan_repository.get_by_id(str(plan_id))
    if not route_plan:
        raise HTTPException(
            status_code=404, detail=f"Route plan with id {plan_id} not found")

    handler = ChangeRoutePlanStatusHandler(route_plan_repository._uow)
    await handler.handle(ChangeRoutePlanStatusCommand(
        id=str(plan_id),
        trigger="complete_planning"
    ))
    return OperationResponse(
        success=True,
        message="路线计划规划完成"
    )


@router.post("/{plan_id}/mark-ready", response_model=OperationResponse)
async def mark_ready(
    plan_id: UUID,
    route_plan_repository: AbstractRoutePlanRepository = Depends(
        get_route_plan_repository)
) -> OperationResponse:
    """标记就绪

    Args:
        plan_id: 路线计划ID
        route_plan_repository: 路线计划仓储

    Returns:
        OperationResponse: 操作响应
    """
    route_plan = await route_plan_repository.get_by_id(str(plan_id))
    if not route_plan:
        raise HTTPException(
            status_code=404, detail=f"Route plan with id {plan_id} not found")

    handler = ChangeRoutePlanStatusHandler(route_plan_repository._uow)
    await handler.handle(ChangeRoutePlanStatusCommand(
        id=str(plan_id),
        trigger="mark_ready"
    ))
    return OperationResponse(
        success=True,
        message="路线计划已就绪"
    )


@router.post("/{plan_id}/dispatch", response_model=OperationResponse)
async def dispatch_route_plan(
    plan_id: UUID,
    route_plan_repository: AbstractRoutePlanRepository = Depends(
        get_route_plan_repository)
) -> OperationResponse:
    """派发路线计划

    Args:
        plan_id: 路线计划ID
        route_plan_repository: 路线计划仓储

    Returns:
        OperationResponse: 操作响应
    """
    route_plan = await route_plan_repository.get_by_id(str(plan_id))
    if not route_plan:
        raise HTTPException(
            status_code=404, detail=f"Route plan with id {plan_id} not found")

    handler = ChangeRoutePlanStatusHandler(route_plan_repository._uow)
    await handler.handle(ChangeRoutePlanStatusCommand(
        id=str(plan_id),
        trigger="dispatch"
    ))
    return OperationResponse(
        success=True,
        message="路线计划派发成功"
    )


@router.post("/{plan_id}/complete", response_model=OperationResponse)
async def complete_route_plan(
    plan_id: UUID,
    route_plan_repository: AbstractRoutePlanRepository = Depends(
        get_route_plan_repository)
) -> OperationResponse:
    """完成路线计划

    Args:
        plan_id: 路线计划ID
        route_plan_repository: 路线计划仓储

    Returns:
        OperationResponse: 操作响应
    """
    route_plan = await route_plan_repository.get_by_id(str(plan_id))
    if not route_plan:
        raise HTTPException(
            status_code=404, detail=f"Route plan with id {plan_id} not found")

    handler = ChangeRoutePlanStatusHandler(route_plan_repository._uow)
    await handler.handle(ChangeRoutePlanStatusCommand(
        id=str(plan_id),
        trigger="complete"
    ))
    return OperationResponse(
        success=True,
        message="路线计划已完成"
    )


@router.post("/{plan_id}/cancel", response_model=OperationResponse)
async def cancel_route_plan(
    plan_id: UUID,
    route_plan_repository: AbstractRoutePlanRepository = Depends(
        get_route_plan_repository)
) -> OperationResponse:
    """取消路线计划

    Args:
        plan_id: 路线计划ID
        route_plan_repository: 路线计划仓储

    Returns:
        OperationResponse: 操作响应

    Raises:
        HTTPException: 如果路线计划不存在或状态转换失败
    """
    try:
        route_plan = await route_plan_repository.get_by_id(str(plan_id))
        if not route_plan:
            raise HTTPException(
                status_code=404, detail=f"Route plan with id {plan_id} not found")

        handler = ChangeRoutePlanStatusHandler(route_plan_repository._uow)
        await handler.handle(ChangeRoutePlanStatusCommand(
            id=str(plan_id),
            trigger="cancel",
            reason="用户取消"
        ))
        return OperationResponse(
            success=True,
            message="路线计划已取消"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel route plan: {str(e)}"
        )
