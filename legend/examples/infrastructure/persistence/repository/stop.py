"""站点仓储实现

实现站点的仓储接口。
"""
from typing import List, Optional

from sqlalchemy import select

from idp.framework.examples.domain.entity.stop import Stop
from idp.framework.examples.domain.id_generator import IdGenerator
from idp.framework.examples.domain.repository import AbstractStopRepository
from idp.framework.examples.infrastructure.mapper.stop import create_stop_mapper
from idp.framework.examples.infrastructure.persistence.po.stop import StopPO
from idp.framework.infrastructure.mapper.core.mapper import Mapper
from idp.framework.infrastructure.persistence.sqlalchemy.repository import (
    BaseRepository,
)
from idp.framework.infrastructure.persistence.sqlalchemy.uow import SqlAlchemyAsyncUoW


class SqlAlchemyStopRepository(BaseRepository[StopPO], AbstractStopRepository):
    """SQLAlchemy站点仓储实现"""

    def __init__(self, uow: SqlAlchemyAsyncUoW, id_generator: IdGenerator, mapper: Mapper = None):
        """初始化仓储

        Args:
            uow: 工作单元
            id_generator: ID生成器
            mapper: 映射器
        """
        super().__init__(uow.session)
        self._uow = uow
        self.id_generator = id_generator
        self._mapper = mapper or create_stop_mapper()

    async def get_by_tenant_id(self, tenant_id: str) -> List[Stop]:
        """根据租户ID获取站点列表

        Args:
            tenant_id: 租户ID

        Returns:
            List[Stop]: 站点列表
        """
        stmt = select(StopPO).where(StopPO.tenant_id == tenant_id)
        result = await self.session.scalars(stmt)
        return [self._mapper.map_to_source(po) for po in result]

    async def get_all(self) -> List[Stop]:
        """获取所有站点

        Returns:
            List[Stop]: 站点列表
        """
        stmt = select(StopPO)
        result = await self.session.scalars(stmt)
        return [self._mapper.map_to_source(po) for po in result]

    async def get_by_id(self, stop_id: str) -> Optional[Stop]:
        """根据ID获取站点

        Args:
            stop_id: 站点ID

        Returns:
            Optional[Stop]: 站点，如果不存在则返回None
        """
        po = await self.session.get(StopPO, stop_id)
        if not po:
            return None
        return self._mapper.map_to_source(po)

    async def save(self, stop: Stop) -> Stop:
        """保存站点

        Args:
            stop: 站点

        Returns:
            Stop: 保存后的站点
        """
        po = self._mapper.map(stop)
        await self.session.merge(po)
        await self.session.flush()
        return stop

    async def delete(self, id: str) -> None:
        """删除站点

        Args:
            id: 站点ID
        """
        stmt = select(StopPO).where(StopPO.id == id)
        result = await self.session.scalar(stmt)
        if result:
            await self.session.delete(result)
            await self.session.flush()

    async def create(self, entity: Stop) -> Stop:
        """创建站点

        Args:
            entity: 站点实体

        Returns:
            Stop: 创建的站点
        """
        po = self._mapper.map(entity)
        await self.session.merge(po)
        await self.session.flush()
        return entity

    async def update(self, entity: Stop) -> Stop:
        """更新站点

        Args:
            entity: 站点实体

        Returns:
            Stop: 更新后的站点
        """
        po = self._mapper.map(entity)
        await self.session.merge(po)
        await self.session.flush()
        return entity

    async def find(self, **criteria) -> List[Stop]:
        """根据条件查找站点

        Args:
            **criteria: 查询条件

        Returns:
            List[Stop]: 站点列表
        """
        stmt = select(StopPO)
        for key, value in criteria.items():
            if hasattr(StopPO, key):
                stmt = stmt.where(getattr(StopPO, key) == value)
        result = await self.session.scalars(stmt)
        return [self._mapper.map_to_source(po) for po in result]

    async def find_one(self, **criteria) -> Optional[Stop]:
        """根据条件查找单个站点

        Args:
            **criteria: 查询条件

        Returns:
            Optional[Stop]: 站点，如果不存在则返回None
        """
        stmt = select(StopPO)
        for key, value in criteria.items():
            if hasattr(StopPO, key):
                stmt = stmt.where(getattr(StopPO, key) == value)
        result = await self.session.scalar(stmt)
        return self._mapper.map_to_source(result) if result else None

    async def find_all(self) -> List[Stop]:
        """获取所有站点

        Returns:
            List[Stop]: 站点列表
        """
        return await self.get_all()

    async def count(self, **criteria) -> int:
        """计算满足条件的站点数量

        Args:
            **criteria: 查询条件

        Returns:
            int: 站点数量
        """
        from sqlalchemy import func
        stmt = select(func.count()).select_from(StopPO)
        for key, value in criteria.items():
            if hasattr(StopPO, key):
                stmt = stmt.where(getattr(StopPO, key) == value)
        result = await self.session.scalar(stmt)
        return result or 0

    async def exists(self, id: str) -> bool:
        """检查站点是否存在

        Args:
            id: 站点ID

        Returns:
            bool: 是否存在
        """
        return await self.get_by_id(id) is not None

    async def batch_create(self, entities: List[Stop]) -> List[Stop]:
        """批量创建站点

        Args:
            entities: 站点列表

        Returns:
            List[Stop]: 创建后的站点列表
        """
        for entity in entities:
            await self.create(entity)
        return entities

    async def batch_update(self, entities: List[Stop]) -> List[Stop]:
        """批量更新站点

        Args:
            entities: 站点列表

        Returns:
            List[Stop]: 更新后的站点列表
        """
        for entity in entities:
            await self.update(entity)
        return entities

    async def batch_delete(self, entities: List[Stop]) -> None:
        """批量删除站点

        Args:
            entities: 站点列表
        """
        for entity in entities:
            await self.delete(str(entity.id))

    async def get_by_name(self, name: str) -> Optional[Stop]:
        """根据名称获取站点

        Args:
            name: 站点名称

        Returns:
            Optional[Stop]: 站点，如果不存在则返回None
        """
        stmt = select(StopPO).where(StopPO.name == name)
        result = await self.session.scalar(stmt)
        return self._mapper.map_to_source(result) if result else None

    async def get_by_address(self, address: str) -> Optional[Stop]:
        """根据地址获取站点

        Args:
            address: 站点地址

        Returns:
            Optional[Stop]: 站点，如果不存在则返回None
        """
        stmt = select(StopPO).where(StopPO.address == address)
        result = await self.session.scalar(stmt)
        return self._mapper.map_to_source(result) if result else None
