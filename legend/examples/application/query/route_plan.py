"""路线计划查询

定义路线计划的查询对象。
"""
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from idp.framework.examples.api.schema.stop import StopResponse
from idp.framework.examples.domain.vo.route_plan_status import RoutePlanStatus


class GetRoutePlanQuery(BaseModel):
    """获取路线计划查询"""

    plan_id: UUID = Field(..., description="路线计划ID")


class ListRoutePlansQuery(BaseModel):
    """列出路线计划查询"""

    status: Optional[RoutePlanStatus] = Field(None, description="路线计划状态")
    tenant_id: Optional[str] = Field(None, description="租户ID")


class RoutePlanDTO(BaseModel):
    """路线计划数据传输对象"""

    id: str = Field(..., description="路线计划ID")
    stops: List[str] = Field(..., description="站点ID列表")
    status: RoutePlanStatus = Field(..., description="路线计划状态")
    tenant_id: Optional[str] = Field(None, description="租户ID")

    class Config:
        from_attributes = True
