"""Route Plan 领域服务

定义路线计划相关的领域服务。
"""
from typing import List, Optional

from idp.framework.domain.service.base import DomainService
from idp.framework.examples.domain.aggregate.route_plan import RoutePlan
from idp.framework.examples.domain.repository import AbstractRoutePlanRepository


class RoutePlanService(DomainService):
    """路线计划领域服务"""

    def __init__(self, repository: AbstractRoutePlanRepository):
        """初始化路线计划领域服务

        Args:
            repository: 路线计划仓储
        """
        self._repository = repository

    async def create_route_plan(
        self,
        stops: List[str],
        tenant_id: Optional[str] = None
    ) -> RoutePlan:
        """创建路线计划

        Args:
            stops: 站点列表
            tenant_id: 租户ID

        Returns:
            RoutePlan: 创建的路线计划
        """
        route_plan = RoutePlan(stops=stops, tenant_id=tenant_id)
        await self._repository.save(route_plan)
        return route_plan

    async def get_route_plan(self, plan_id: str) -> Optional[RoutePlan]:
        """获取路线计划

        Args:
            plan_id: 路线计划ID

        Returns:
            Optional[RoutePlan]: 路线计划实例，如果不存在则返回None
        """
        return await self._repository.get_by_id(plan_id)

    async def get_all_route_plans(self) -> List[RoutePlan]:
        """获取所有路线计划

        Returns:
            List[RoutePlan]: 路线计划列表
        """
        return await self._repository.get_all()

    async def delete_route_plan(self, plan_id: str) -> None:
        """删除路线计划

        Args:
            plan_id: 路线计划ID
        """
        await self._repository.delete(plan_id)
