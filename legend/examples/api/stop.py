"""站点相关的API路由"""
from typing import List, Optional

from examples.application.di.stop import get_stop_repository
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from idp.framework.examples.api.schema.stop import (
    CreateStopRequest,
    StopResponse,
    UpdateStopContactRequest,
    UpdateStopLocationRequest,
    UpdateStopRequest,
)
from idp.framework.examples.application.command.stop import (
    ActivateStopCommand,
    CreateStopCommand,
    DeactivateStopCommand,
    UpdateStopCommand,
    UpdateStopContactCommand,
    UpdateStopLocationCommand,
)
from idp.framework.examples.application.service.stop import StopApplicationService
from idp.framework.examples.domain.service.stop import StopDomainService
from idp.framework.examples.domain.vo.location import Location
from idp.framework.examples.infrastructure.persistence.repository.stop import (
    AbstractStopRepository,
)

router = APIRouter(prefix="/stops", tags=["stops"])


def get_stop_application_service(
    stop_repository: AbstractStopRepository = Depends(get_stop_repository),
    stop_domain_service: StopDomainService = Depends(
        lambda: StopDomainService())
) -> StopApplicationService:
    """获取站点应用服务

    Args:
        stop_repository: 站点仓储
        stop_domain_service: 站点领域服务

    Returns:
        StopApplicationService: 站点应用服务
    """
    return StopApplicationService(stop_repository, stop_domain_service)


@router.post("", response_model=StopResponse)
async def create_stop(
    request: CreateStopRequest,
    service: StopApplicationService = Depends(get_stop_application_service)
) -> StopResponse:
    """创建站点

    Args:
        request: 创建站点请求
        service: 站点应用服务

    Returns:
        StopResponse: 站点响应
    """
    try:
        command = CreateStopCommand(
            name=request.name,
            address=request.address,
            location=request.location.to_vo() if request.location else None,
            contact=request.contact.to_vo() if request.contact else None,
            description=request.description,
            tenant_id=request.tenant_id
        )
        stop = await service.create_stop(command)
        return StopResponse.from_domain(stop)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{stop_id}", response_model=StopResponse)
async def update_stop(
    stop_id: str,
    request: UpdateStopRequest,
    service: StopApplicationService = Depends(get_stop_application_service)
) -> StopResponse:
    """更新站点

    Args:
        stop_id: 站点ID
        request: 更新站点请求
        service: 站点应用服务

    Returns:
        StopResponse: 站点响应
    """
    try:
        command = UpdateStopCommand(
            stop_id=stop_id,
            name=request.name,
            address=request.address,
            location=request.location.to_vo() if request.location else None,
            contact=request.contact.to_vo() if request.contact else None,
            description=request.description,
            tenant_id=request.tenant_id
        )
        stop = await service.update_stop(command)
        return StopResponse.from_domain(stop)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{stop_id}/location", response_model=StopResponse)
async def update_stop_location(
    stop_id: str,
    request: UpdateStopLocationRequest,
    service: StopApplicationService = Depends(get_stop_application_service)
) -> StopResponse:
    """更新站点位置

    Args:
        stop_id: 站点ID
        request: 更新站点位置请求
        service: 站点应用服务

    Returns:
        StopResponse: 站点响应
    """
    try:
        command = UpdateStopLocationCommand(
            stop_id=stop_id,
            location=Location(latitude=request.latitude,
                              longitude=request.longitude),
            tenant_id=request.tenant_id
        )
        stop = await service.update_stop_location(command)
        return StopResponse.from_domain(stop)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{stop_id}/contact", response_model=StopResponse)
async def update_stop_contact(
    stop_id: str,
    request: UpdateStopContactRequest,
    service: StopApplicationService = Depends(get_stop_application_service)
) -> StopResponse:
    """更新站点联系人

    Args:
        stop_id: 站点ID
        request: 更新站点联系人请求
        service: 站点应用服务

    Returns:
        StopResponse: 站点响应
    """
    try:
        command = UpdateStopContactCommand(
            stop_id=stop_id,
            name=request.name,
            phone=request.phone,
            email=request.email,
            tenant_id=request.tenant_id
        )
        stop = await service.update_stop_contact(command)
        return StopResponse.from_domain(stop)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{stop_id}/deactivate", response_model=StopResponse)
async def deactivate_stop(
    stop_id: str,
    tenant_id: str,
    service: StopApplicationService = Depends(get_stop_application_service)
) -> StopResponse:
    """停用站点

    Args:
        stop_id: 站点ID
        tenant_id: 租户ID
        service: 站点应用服务

    Returns:
        StopResponse: 站点响应
    """
    try:
        command = DeactivateStopCommand(stop_id=stop_id, tenant_id=tenant_id)
        stop = await service.deactivate_stop(command)
        return StopResponse.from_domain(stop)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{stop_id}/activate", response_model=StopResponse)
async def activate_stop(
    stop_id: str,
    tenant_id: str,
    service: StopApplicationService = Depends(get_stop_application_service)
) -> StopResponse:
    """启用站点

    Args:
        stop_id: 站点ID
        tenant_id: 租户ID
        service: 站点应用服务

    Returns:
        StopResponse: 站点响应
    """
    try:
        command = ActivateStopCommand(stop_id=stop_id, tenant_id=tenant_id)
        stop = await service.activate_stop(command)
        return StopResponse.from_domain(stop)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/nearest", response_model=Optional[StopResponse])
async def find_nearest_stop(
    latitude: float,
    longitude: float,
    service: StopApplicationService = Depends(get_stop_application_service)
) -> Optional[StopResponse]:
    """查找最近的站点

    Args:
        latitude: 纬度
        longitude: 经度
        service: 站点应用服务

    Returns:
        Optional[StopResponse]: 站点响应，如果没有找到则返回None
    """
    stop = await service.find_nearest_stop(latitude, longitude)
    return StopResponse.from_domain(stop) if stop else None


@router.post("/validate-sequence", response_model=bool)
async def validate_stop_sequence(
    stop_ids: List[str],
    service: StopApplicationService = Depends(get_stop_application_service)
) -> bool:
    """验证站点序列的合理性

    Args:
        stop_ids: 站点ID列表
        service: 站点应用服务

    Returns:
        bool: 是否合理
    """
    return await service.validate_stop_sequence(stop_ids)
