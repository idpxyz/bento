"""路线计划仓储接口

定义路线计划仓储接口。
"""
from abc import abstractmethod
from typing import List, Optional

from idp.framework.domain.repository import AbstractRepository
from idp.framework.examples.domain.aggregate.route_plan import RoutePlan
from idp.framework.examples.domain.vo.route_plan_status import RoutePlanStatus


class AbstractRoutePlanRepository(AbstractRepository[RoutePlan, str]):
    """路线计划仓储接口"""

    @abstractmethod
    async def get_by_id(self, id: str) -> Optional[RoutePlan]:
        """根据ID获取路线计划

        Args:
            id: 路线计划ID

        Returns:
            Optional[RoutePlan]: 路线计划实例，如果不存在则返回None
        """
        raise NotImplementedError

    @abstractmethod
    async def get_all(self) -> List[RoutePlan]:
        """获取所有路线计划

        Returns:
            List[RoutePlan]: 路线计划列表
        """
        raise NotImplementedError

    @abstractmethod
    async def save(self, route_plan: RoutePlan) -> None:
        """保存路线计划

        Args:
            route_plan: 路线计划实例
        """
        raise NotImplementedError

    @abstractmethod
    async def delete(self, id: str) -> None:
        """删除路线计划

        Args:
            id: 路线计划ID
        """
        raise NotImplementedError

    @abstractmethod
    async def get_by_status(self, status: RoutePlanStatus) -> List[RoutePlan]:
        """根据状态获取路线计划列表

        Args:
            status: 路线计划状态

        Returns:
            List[RoutePlan]: 路线计划列表
        """
        raise NotImplementedError

    @abstractmethod
    async def get_by_tenant_id(self, tenant_id: str) -> List[RoutePlan]:
        """根据租户ID获取路线计划列表

        Args:
            tenant_id: 租户ID

        Returns:
            List[RoutePlan]: 路线计划列表
        """
        raise NotImplementedError
