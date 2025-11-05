"""站点相关的依赖注入"""
from fastapi import Depends

from idp.framework.examples.domain.id_generator import IdGenerator
from idp.framework.examples.domain.repository import AbstractStopRepository
from idp.framework.examples.infrastructure.id_generator import UuidIdGenerator
from idp.framework.examples.infrastructure.mapper.stop import create_stop_mapper
from idp.framework.examples.infrastructure.persistence.repository.stop import (
    SqlAlchemyStopRepository,
)
from idp.framework.infrastructure.persistence.sqlalchemy.di import get_uow
from idp.framework.infrastructure.persistence.sqlalchemy.uow import SqlAlchemyAsyncUoW


def get_id_generator() -> IdGenerator:
    """获取ID生成器

    Returns:
        IdGenerator: ID生成器
    """
    return UuidIdGenerator()


def get_stop_mapper():
    return create_stop_mapper()


def get_stop_repository(
    uow: SqlAlchemyAsyncUoW = Depends(get_uow),
    id_generator: IdGenerator = Depends(get_id_generator),
    mapper=Depends(get_stop_mapper)
) -> AbstractStopRepository:
    """获取站点仓储

    Args:
        uow: 工作单元
        id_generator: ID生成器
        mapper: Stop映射器

    Returns:
        AbstractStopRepository: 站点仓储
    """
    return SqlAlchemyStopRepository(uow, id_generator, mapper)
