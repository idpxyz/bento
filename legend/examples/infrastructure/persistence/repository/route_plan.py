"""路线计划仓储实现

实现路线计划的仓储接口。
"""
from typing import List, Optional

from sqlalchemy import delete, insert, select

from idp.framework.examples.domain.aggregate.route_plan import RoutePlan
from idp.framework.examples.domain.repository.route_plan import (
    AbstractRoutePlanRepository,
)
from idp.framework.examples.domain.vo.route_plan_status import RoutePlanStatus
from idp.framework.examples.infrastructure.id_generator import IdGenerator
from idp.framework.examples.infrastructure.mapper.route_plan import (
    create_route_plan_mapper,
)
from idp.framework.examples.infrastructure.persistence.po.route_plan import (
    RoutePlanPO,
    route_plan_stop,
)
from idp.framework.examples.infrastructure.persistence.po.stop import StopPO
from idp.framework.infrastructure.mapper.core.mapper import Mapper
from idp.framework.infrastructure.persistence.sqlalchemy.repository import (
    BaseRepository,
)
from idp.framework.infrastructure.persistence.sqlalchemy.uow import SqlAlchemyAsyncUoW


class SqlAlchemyRoutePlanRepository(BaseRepository[RoutePlanPO], AbstractRoutePlanRepository):
    """SQLAlchemy路线计划仓储实现"""

    def __init__(self, uow: SqlAlchemyAsyncUoW, id_generator: IdGenerator, mapper: Mapper = None):
        """初始化仓储

        Args:
            uow: 工作单元
            id_generator: ID生成器
            mapper: 映射器
        """
        super().__init__(uow.session)
        self._uow = uow
        self._id_generator = id_generator
        self._mapper = mapper or create_route_plan_mapper()

    async def get_by_status(self, status: RoutePlanStatus) -> List[RoutePlan]:
        """根据状态获取路线计划列表

        Args:
            status: 路线计划状态

        Returns:
            List[RoutePlan]: 路线计划列表
        """
        stmt = select(RoutePlanPO).where(RoutePlanPO.status == status)
        result = await self._uow.session.scalars(stmt)
        route_plans = []
        for po in result.unique():
            stmt = select(route_plan_stop.c.stop_id).where(
                route_plan_stop.c.route_plan_id == po.id
            ).order_by(route_plan_stop.c.sequence)
            stop_ids_result = await self._uow.session.scalars(stmt)
            stop_ids = [str(stop_id) for stop_id in stop_ids_result]
            entity = RoutePlan(
                stops=stop_ids,
                tenant_id=po.tenant_id,
                id=po.id,
                status=po.status,
                name=po.name,
                description=po.description,
                is_active=po.is_active,
                register_event=False
            )
            route_plans.append(entity)
        return route_plans

    async def get_by_tenant_id(self, tenant_id: str) -> List[RoutePlan]:
        """根据租户ID获取路线计划列表

        Args:
            tenant_id: 租户ID

        Returns:
            List[RoutePlan]: 路线计划列表
        """
        stmt = select(RoutePlanPO).where(RoutePlanPO.tenant_id == tenant_id)
        result = await self._uow.session.scalars(stmt)
        route_plans = []
        for po in result.unique():
            stmt = select(route_plan_stop.c.stop_id).where(
                route_plan_stop.c.route_plan_id == po.id
            ).order_by(route_plan_stop.c.sequence)
            stop_ids_result = await self._uow.session.scalars(stmt)
            stop_ids = [str(stop_id) for stop_id in stop_ids_result]
            entity = RoutePlan(
                stops=stop_ids,
                tenant_id=po.tenant_id,
                id=po.id,
                status=po.status,
                name=po.name,
                description=po.description,
                is_active=po.is_active,
                register_event=False
            )
            route_plans.append(entity)
        return route_plans

    async def get_all(self) -> List[RoutePlan]:
        """获取所有路线计划

        Returns:
            List[RoutePlan]: 路线计划列表
        """
        stmt = select(RoutePlanPO)
        result = await self._uow.session.scalars(stmt)
        route_plans = []
        for po in result.unique():
            stmt = select(route_plan_stop.c.stop_id).where(
                route_plan_stop.c.route_plan_id == po.id
            ).order_by(route_plan_stop.c.sequence)
            stop_ids_result = await self._uow.session.scalars(stmt)
            stop_ids = [str(stop_id) for stop_id in stop_ids_result]
            entity = RoutePlan(
                stops=stop_ids,
                tenant_id=po.tenant_id,
                id=po.id,
                status=po.status,
                name=po.name,
                description=po.description,
                is_active=po.is_active,
                register_event=False
            )
            route_plans.append(entity)
        return route_plans

    async def get_by_id(self, id: str) -> Optional[RoutePlan]:
        """根据ID获取路线计划

        Args:
            id: 路线计划ID

        Returns:
            Optional[RoutePlan]: 路线计划实例，如果不存在则返回None
        """
        stmt = select(RoutePlanPO).where(RoutePlanPO.id == id)
        po = await self._uow.session.scalar(stmt)
        if not po:
            return None
        stmt = select(route_plan_stop.c.stop_id).where(
            route_plan_stop.c.route_plan_id == id
        ).order_by(route_plan_stop.c.sequence)
        stop_ids_result = await self._uow.session.scalars(stmt)
        stop_ids = [str(stop_id) for stop_id in stop_ids_result]
        entity = RoutePlan(
            stops=stop_ids,
            tenant_id=po.tenant_id,
            id=po.id,
            status=po.status,
            name=po.name,
            description=po.description,
            is_active=po.is_active,
            register_event=False
        )
        return entity

    async def save(self, route_plan: RoutePlan) -> RoutePlan:
        """保存路线计划

        Args:
            route_plan: 路线计划

        Returns:
            RoutePlan: 保存后的路线计划
        """
        po = self._mapper.map(route_plan)
        await self._uow.session.merge(po)
        await self._uow.session.flush()
        await self._uow.session.execute(
            delete(route_plan_stop).where(
                route_plan_stop.c.route_plan_id == str(route_plan.id))
        )
        await self._uow.session.flush()
        for i, stop_id in enumerate(route_plan.stops):
            await self._uow.session.execute(
                insert(route_plan_stop).values(
                    route_plan_id=str(route_plan.id),
                    stop_id=stop_id,
                    sequence=int(i)
                )
            )
        await self._uow.session.flush()
        return route_plan

    async def _create_route_plan_stops(self, route_plan_id: str, stop_ids: List[str]) -> None:
        """创建路线计划-站点关联

        Args:
            route_plan_id: 路线计划ID
            stop_ids: 站点ID列表，按顺序排列
        """
        # 删除现有的关联
        await self._uow.session.execute(
            route_plan_stop.delete().where(route_plan_stop.c.route_plan_id == route_plan_id)
        )
        await self._uow.session.flush()  # 确保删除操作完成

        # 创建新的关联
        for sequence, stop_id in enumerate(stop_ids):
            await self._uow.session.execute(
                insert(route_plan_stop).values(
                    route_plan_id=route_plan_id,
                    stop_id=stop_id,
                    sequence=int(sequence)  # 确保sequence是整数
                )
            )
        await self._uow.session.flush()  # 确保插入操作完成

    async def delete(self, id: str) -> None:
        """删除路线计划

        Args:
            id: 路线计划ID
        """
        stmt = select(RoutePlanPO).where(RoutePlanPO.id == id)
        result = await self._uow.session.scalar(stmt)
        if result:
            await self._uow.session.delete(result)

    async def create(self, entity: RoutePlan) -> None:
        """创建路线计划

        Args:
            entity: 路线计划实体
        """
        po = self._mapper.map(entity)
        await self._uow.session.merge(po)
        await self._uow.session.flush()
        for stop_id in entity.stops:
            stmt = select(StopPO).where(StopPO.id == stop_id)
            stop = await self._uow.session.scalar(stmt)
            if not stop:
                raise ValueError(f"Stop with ID {stop_id} does not exist")
        for i, stop_id in enumerate(entity.stops):
            await self._uow.session.execute(
                insert(route_plan_stop).values(
                    route_plan_id=str(entity.id),
                    stop_id=stop_id,
                    sequence=int(i),
                    tenant_id=entity.tenant_id
                )
            )
        await self._uow.session.flush()
        return None

    async def update(self, entity: RoutePlan) -> RoutePlan:
        """更新路线计划

        Args:
            entity: 路线计划实体

        Returns:
            RoutePlan: 更新后的路线计划
        """
        po = self._mapper.map(entity)
        await self._uow.session.merge(po)
        await self._uow.session.flush()
        await self._uow.session.execute(
            delete(route_plan_stop).where(
                route_plan_stop.c.route_plan_id == str(entity.id))
        )
        await self._uow.session.flush()
        for i, stop_id in enumerate(entity.stops):
            await self._uow.session.execute(
                insert(route_plan_stop).values(
                    route_plan_id=str(entity.id),
                    stop_id=stop_id,
                    sequence=int(i),
                    tenant_id=entity.tenant_id
                )
            )
        await self._uow.session.flush()
        return entity

    async def find(self, **criteria) -> List[RoutePlan]:
        """根据条件查找路线计划

        Args:
            **criteria: 查询条件

        Returns:
            List[RoutePlan]: 路线计划列表
        """
        stmt = select(RoutePlanPO)
        for key, value in criteria.items():
            if hasattr(RoutePlanPO, key):
                stmt = stmt.where(getattr(RoutePlanPO, key) == value)
        result = await self._uow.session.scalars(stmt)
        route_plans = []
        for po in result.unique():
            stmt = select(route_plan_stop.c.stop_id).where(
                route_plan_stop.c.route_plan_id == po.id
            ).order_by(route_plan_stop.c.sequence)
            stop_ids_result = await self._uow.session.scalars(stmt)
            stop_ids = [str(stop_id) for stop_id in stop_ids_result]
            entity = RoutePlan(
                stops=stop_ids,
                tenant_id=po.tenant_id,
                id=po.id,
                status=po.status,
                name=po.name,
                description=po.description,
                is_active=po.is_active
            )
            route_plans.append(entity)
        return route_plans

    async def find_one(self, **criteria) -> Optional[RoutePlan]:
        """根据条件查找单个路线计划

        Args:
            **criteria: 查询条件

        Returns:
            Optional[RoutePlan]: 路线计划，如果不存在则返回None
        """
        stmt = select(RoutePlanPO)
        for key, value in criteria.items():
            if hasattr(RoutePlanPO, key):
                stmt = stmt.where(getattr(RoutePlanPO, key) == value)
        po = await self._uow.session.scalar(stmt)
        if not po:
            return None
        stmt = select(route_plan_stop.c.stop_id).where(
            route_plan_stop.c.route_plan_id == po.id
        ).order_by(route_plan_stop.c.sequence)
        stop_ids_result = await self._uow.session.scalars(stmt)
        stop_ids = [str(stop_id) for stop_id in stop_ids_result]
        entity = RoutePlan(
            stops=stop_ids,
            tenant_id=po.tenant_id,
            id=po.id,
            status=po.status,
            name=po.name,
            description=po.description,
            is_active=po.is_active
        )
        return entity

    async def find_all(self) -> List[RoutePlan]:
        """获取所有路线计划

        Returns:
            List[RoutePlan]: 路线计划列表
        """
        return await self.get_all()

    async def count(self, **criteria) -> int:
        """计算满足条件的路线计划数量

        Args:
            **criteria: 查询条件

        Returns:
            int: 路线计划数量
        """
        from sqlalchemy import func
        stmt = select(func.count()).select_from(RoutePlanPO)
        for key, value in criteria.items():
            if hasattr(RoutePlanPO, key):
                stmt = stmt.where(getattr(RoutePlanPO, key) == value)
        result = await self._uow.session.scalar(stmt)
        return result or 0

    async def exists(self, id: str) -> bool:
        """检查路线计划是否存在

        Args:
            id: 路线计划ID

        Returns:
            bool: 是否存在
        """
        return await self.get_by_id(id) is not None

    async def batch_create(self, entities: List[RoutePlan]) -> List[RoutePlan]:
        """批量创建路线计划

        Args:
            entities: 路线计划列表

        Returns:
            List[RoutePlan]: 创建后的路线计划列表
        """
        for entity in entities:
            await self.create(entity)
        return entities

    async def batch_update(self, entities: List[RoutePlan]) -> List[RoutePlan]:
        """批量更新路线计划

        Args:
            entities: 路线计划列表

        Returns:
            List[RoutePlan]: 更新后的路线计划列表
        """
        for entity in entities:
            await self.update(entity)
        return entities

    async def batch_delete(self, entities: List[RoutePlan]) -> None:
        """批量删除路线计划

        Args:
            entities: 路线计划列表
        """
        for entity in entities:
            await self.delete(str(entity.id))
