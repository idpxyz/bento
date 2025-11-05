"""路线计划 API Schema

定义路线计划的请求和响应模型。
"""
from typing import List, Optional

from examples.application.query.route_plan import RoutePlanDTO
from pydantic import BaseModel, Field

from idp.framework.examples.api.schema.stop import StopResponse
from idp.framework.examples.domain.vo.route_plan_status import RoutePlanStatus


class CreateRoutePlanRequest(BaseModel):
    """创建路线计划请求"""
    stops: List[str] = Field(..., description="站点ID列表")
    tenant_id: Optional[str] = Field(None, description="租户ID")


class UpdateRoutePlanRequest(BaseModel):
    """更新路线计划请求"""
    stops: List[str] = Field(..., description="站点ID列表")
    tenant_id: Optional[str] = Field(None, description="租户ID")


class RoutePlanResponse(BaseModel):
    """路线计划响应"""
    id: str = Field(..., description="路线计划ID")
    stops: List[StopResponse] = Field(..., description="站点列表")
    status: RoutePlanStatus = Field(..., description="路线计划状态")
    tenant_id: Optional[str] = Field(None, description="租户ID")

    @classmethod
    def from_dto(cls, dto: "RoutePlanDTO") -> "RoutePlanResponse":
        """从DTO创建响应

        Args:
            dto: 路线计划DTO

        Returns:
            RoutePlanResponse: 路线计划响应
        """
        return cls(
            id=dto.id,
            stops=dto.stops,
            status=dto.status,
            tenant_id=dto.tenant_id
        )

    class Config:
        """Pydantic 配置"""
        from_attributes = True  # 允许从ORM模型创建
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "stops": ["stop1", "stop2", "stop3"],
                "status": "READY",
                "tenant_id": "tenant1"
            }
        }


class CreateRoutePlanResponse(BaseModel):
    """创建路线计划响应"""
    id: str = Field(..., description="路线计划ID")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }


class OperationResponse(BaseModel):
    """操作响应"""
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="操作结果消息")
