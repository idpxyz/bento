from fastapi import Depends

from idp.framework.application.command_bus import CommandBus
from idp.framework.infrastructure.persistence import AsyncUnitOfWork, get_uow


def get_command_bus(
    uow: AsyncUnitOfWork = Depends(get_uow)
) -> CommandBus:
    """
    FastAPI 依赖注入：提供已注入 UnitOfWork 的 CommandBus 实例。
    """
    return CommandBus(uow=uow)