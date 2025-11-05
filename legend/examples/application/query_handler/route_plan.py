"""路线计划查询处理器

处理路线计划的查询。
"""
from abc import ABC, abstractmethod
from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel

from idp.framework.examples.api.schema.stop import StopResponse
from idp.framework.examples.application.query.route_plan import (
    GetRoutePlanQuery,
    ListRoutePlansQuery,
    RoutePlanDTO,
)
from idp.framework.examples.domain.repository import AbstractRoutePlanRepository
from idp.framework.examples.infrastructure.persistence.po.stop import StopPO

# Local QueryHandler implementation for examples
QueryType = TypeVar('QueryType', bound=BaseModel)
ResultType = TypeVar('ResultType')


class QueryHandler(Generic[QueryType, ResultType], ABC):
    """查询处理器基类 (示例用)"""

    @abstractmethod
    async def handle(self, query: QueryType) -> ResultType:
        """处理查询"""
        pass


class GetRoutePlanHandler(QueryHandler[GetRoutePlanQuery, Optional[RoutePlanDTO]]):
    """获取路线计划查询处理器"""

    def __init__(self, route_plan_repository: AbstractRoutePlanRepository):
        """初始化处理器

        Args:
            route_plan_repository: 路线计划仓储
        """
        self._route_plan_repository = route_plan_repository

    async def handle(self, query: GetRoutePlanQuery) -> Optional[RoutePlanDTO]:
        """处理获取路线计划查询

        Args:
            query: 获取路线计划查询

        Returns:
            Optional[RoutePlanDTO]: 路线计划数据传输对象，如果不存在则返回None
        """
        route_plan = await self._route_plan_repository.get_by_id(str(query.plan_id))
        if not route_plan:
            return None

        # 获取完整的站点信息
        stops = []
        for stop_id in route_plan.stops:
            stop = await self._route_plan_repository._uow.session.get(StopPO, stop_id)
            if stop:
                stops.append(StopResponse.model_validate(stop))

        return RoutePlanDTO(
            id=route_plan.id,
            stops=stops,
            status=route_plan.status,
            tenant_id=route_plan.tenant_id
        )


class ListRoutePlansHandler(QueryHandler[ListRoutePlansQuery, List[RoutePlanDTO]]):
    """列出路线计划查询处理器"""

    def __init__(self, route_plan_repository: AbstractRoutePlanRepository):
        """初始化处理器

        Args:
            route_plan_repository: 路线计划仓储
        """
        self._route_plan_repository = route_plan_repository

    async def handle(self, query: ListRoutePlansQuery) -> List[RoutePlanDTO]:
        """处理列出路线计划查询

        Args:
            query: 列出路线计划查询

        Returns:
            List[RoutePlanDTO]: 路线计划数据传输对象列表
        """
        if query.status:
            route_plans = await self._route_plan_repository.get_by_status(query.status)
        elif query.tenant_id:
            route_plans = await self._route_plan_repository.get_by_tenant_id(query.tenant_id)
        else:
            route_plans = await self._route_plan_repository.get_all()

        result = []
        for route_plan in route_plans:
            # 获取完整的站点信息
            stops = []
            for stop_id in route_plan.stops:
                stop = await self._route_plan_repository._uow.session.get(StopPO, stop_id)
                if stop:
                    stops.append(StopResponse.model_validate(stop))

            result.append(RoutePlanDTO(
                id=route_plan.id,
                stops=stops,
                status=route_plan.status,
                tenant_id=route_plan.tenant_id
            ))

        return result
