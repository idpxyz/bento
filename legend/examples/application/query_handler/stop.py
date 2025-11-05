"""站点相关的查询处理器"""
from abc import ABC, abstractmethod
from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from idp.framework.examples.application.query.stop import GetStopQuery, ListStopsQuery
from idp.framework.examples.domain.entity.stop import Stop
from idp.framework.examples.domain.repository import AbstractStopRepository
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


class GetStopHandler(QueryHandler[GetStopQuery, Optional[Stop]]):
    """获取站点查询处理器"""

    def __init__(self, repository: AbstractStopRepository):
        """初始化

        Args:
            uow: 工作单元
        """
        self._repository = repository

    async def handle(self, query: GetStopQuery) -> Optional[Stop]:
        """处理获取站点查询

        Args:
            query: 获取站点查询

        Returns:
            Optional[Stop]: 站点，如果不存在则返回 None
        """
        stop = await self._repository.get_by_id(query.stop_id)
        if not stop:
            return None
        return stop


class ListStopsHandler(QueryHandler[ListStopsQuery, List[Stop]]):
    """列出站点查询处理器"""

    def __init__(self, repository: AbstractStopRepository):
        """初始化

        Args:
            uow: 工作单元
        """
        self._repository = repository

    async def handle(self, query: ListStopsQuery) -> List[Stop]:
        """处理列出站点查询

        Args:
            query: 列出站点查询

        Returns:
            List[Stop]: 站点列表
        """
        # 构建查询条件
        criteria = {}
        if query.name:
            criteria["name"] = query.name
        if query.address:
            criteria["address"] = query.address

        # 使用仓储的find方法
        result = await self._repository.find(**criteria)

        # 应用分页
        start = query.skip
        end = start + query.limit
        return result[start:end]
