"""路线计划命令处理器

处理路线计划的命令。
"""
from typing import Optional
from uuid import uuid4

from idp.framework.application.command.handler import CommandHandler
from idp.framework.examples.application.command.route_plan import (
    ChangeRoutePlanStatusCommand,
    CreateRoutePlanCommand,
    UpdateRoutePlanCommand,
)
from idp.framework.examples.domain.aggregate.route_plan import RoutePlan
from idp.framework.examples.domain.vo.route_plan_status import RoutePlanStatus
from idp.framework.examples.infrastructure.persistence.repository.route_plan import (
    SqlAlchemyRoutePlanRepository,
)
from idp.framework.examples.infrastructure.id_generator import (
    UuidIdGenerator,
)
from idp.framework.infrastructure.persistence.sqlalchemy.uow import SqlAlchemyAsyncUoW


class CreateRoutePlanHandler(CommandHandler[CreateRoutePlanCommand, str]):
    """创建路线计划命令处理器"""

    def __init__(self, uow: SqlAlchemyAsyncUoW):
        """初始化处理器

        Args:
            uow: 工作单元
        """
        self._uow = uow
        self._id_generator = UuidIdGenerator()
        self._repository = SqlAlchemyRoutePlanRepository(
            uow, self._id_generator)

    async def handle(self, command: CreateRoutePlanCommand) -> str:
        """处理创建路线计划命令

        Args:
            command: 创建路线计划命令

        Returns:
            str: 路线计划ID
        """
        plan_id = str(uuid4())
        route_plan = RoutePlan(
            id=plan_id,
            tenant_id=command.tenant_id,
            stops=command.stops,
            status=RoutePlanStatus.DRAFT
        )
        await self._repository.create(route_plan)
        await self._uow.commit()
        return plan_id


class UpdateRoutePlanHandler(CommandHandler[UpdateRoutePlanCommand, None]):
    """更新路线计划命令处理器"""

    def __init__(self, uow: SqlAlchemyAsyncUoW):
        """初始化处理器

        Args:
            uow: 工作单元
        """
        self._uow = uow
        self._id_generator = UuidIdGenerator()
        self._repository = SqlAlchemyRoutePlanRepository(
            uow, self._id_generator)

    async def handle(self, command: UpdateRoutePlanCommand) -> None:
        """处理更新路线计划命令

        Args:
            command: 更新路线计划命令
        """
        route_plan = await self._repository.get_by_id(str(command.id))
        if not route_plan:
            raise ValueError(f"Route plan with id {command.id} not found")

        route_plan.update_stops(command.stops)
        route_plan.update_tenant_id(command.tenant_id)
        await self._uow.commit()


class ChangeRoutePlanStatusHandler(CommandHandler[ChangeRoutePlanStatusCommand, None]):
    """更改路线计划状态命令处理器"""

    def __init__(self, uow: SqlAlchemyAsyncUoW):
        """初始化处理器

        Args:
            uow: 工作单元
        """
        self._uow = uow
        self._id_generator = UuidIdGenerator()
        self._repository = SqlAlchemyRoutePlanRepository(
            uow, self._id_generator)

    async def handle(self, command: ChangeRoutePlanStatusCommand) -> None:
        """处理更改路线计划状态命令

        Args:
            command: 更改路线计划状态命令
        """
        route_plan = await self._repository.get_by_id(str(command.id))
        if not route_plan:
            raise ValueError(f"Route plan with id {command.id} not found")

        route_plan.change_status(command.trigger)
        await self._uow.commit()
