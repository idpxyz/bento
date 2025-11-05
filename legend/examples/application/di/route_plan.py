"""路线计划依赖注入

定义路线计划相关的依赖注入。
"""
from idp.framework.examples.domain.id_generator import IdGenerator
from idp.framework.examples.infrastructure.id_generator import UuidIdGenerator
from idp.framework.examples.infrastructure.persistence.repository.route_plan import (
    SqlAlchemyRoutePlanRepository,
)
from fastapi import Depends


from idp.framework.examples.application.command_handler.route_plan import (
    ChangeRoutePlanStatusHandler,
    CreateRoutePlanHandler,
    UpdateRoutePlanHandler,
)
from idp.framework.examples.domain.repository.route_plan import (
    AbstractRoutePlanRepository,
)
from idp.framework.examples.infrastructure.mapper.route_plan import (
    create_route_plan_mapper,
)
from idp.framework.infrastructure.persistence.sqlalchemy.di import get_uow
from idp.framework.infrastructure.persistence.sqlalchemy.uow import SqlAlchemyAsyncUoW


def get_id_generator() -> IdGenerator:
    """获取ID生成器

    Returns:
        IdGenerator: ID生成器
    """
    return UuidIdGenerator()


def get_route_plan_mapper():
    return create_route_plan_mapper()


async def get_route_plan_repository(
    uow: SqlAlchemyAsyncUoW = Depends(get_uow),
    id_generator: IdGenerator = Depends(get_id_generator),
    mapper=Depends(get_route_plan_mapper)
) -> AbstractRoutePlanRepository:
    """获取路线计划仓储

    Args:
        uow: 工作单元
        id_generator: ID生成器
        mapper: 路线计划映射器

    Returns:
        AbstractRoutePlanRepository: 路线计划仓储
    """
    return SqlAlchemyRoutePlanRepository(uow, id_generator, mapper)


def get_create_route_plan_handler(
    repository: AbstractRoutePlanRepository = Depends(
        get_route_plan_repository)
) -> CreateRoutePlanHandler:
    """获取创建路线计划处理器

    Args:
        repository: 路线计划仓储

    Returns:
        CreateRoutePlanHandler: 创建路线计划处理器
    """
    return CreateRoutePlanHandler(repository)


def get_update_route_plan_handler(
    repository: AbstractRoutePlanRepository = Depends(
        get_route_plan_repository)
) -> UpdateRoutePlanHandler:
    """获取更新路线计划处理器

    Args:
        repository: 路线计划仓储

    Returns:
        UpdateRoutePlanHandler: 更新路线计划处理器
    """
    return UpdateRoutePlanHandler(repository)


def get_change_route_plan_status_handler(
    repository: AbstractRoutePlanRepository = Depends(
        get_route_plan_repository)
) -> ChangeRoutePlanStatusHandler:
    """获取更改路线计划状态处理器

    Args:
        repository: 路线计划仓储

    Returns:
        ChangeRoutePlanStatusHandler: 更改路线计划状态处理器
    """
    return ChangeRoutePlanStatusHandler(repository)
