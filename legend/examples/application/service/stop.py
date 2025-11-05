"""站点应用服务"""
from typing import List, Optional

from idp.framework.examples.application.command.stop import (
    ActivateStopCommand,
    CreateStopCommand,
    DeactivateStopCommand,
    UpdateStopCommand,
    UpdateStopContactCommand,
    UpdateStopLocationCommand,
)
from idp.framework.examples.application.command_handler.stop import (
    ActivateStopHandler,
    CreateStopHandler,
    DeactivateStopHandler,
    UpdateStopContactHandler,
    UpdateStopHandler,
    UpdateStopLocationHandler,
)
from idp.framework.examples.domain.entity.stop import Stop
from idp.framework.examples.domain.service.stop import StopDomainService
from idp.framework.examples.infrastructure.persistence.repository.stop import (
    AbstractStopRepository,
)


class StopApplicationService:
    """站点应用服务"""

    def __init__(
        self,
        stop_repository: AbstractStopRepository,
        stop_domain_service: StopDomainService
    ):
        self._stop_repository = stop_repository
        self._stop_domain_service = stop_domain_service

    async def create_stop(self, command: CreateStopCommand) -> Stop:
        """创建站点

        Args:
            command: 创建站点命令

        Returns:
            Stop: 创建的站点
        """
        handler = CreateStopHandler(self._stop_repository)
        return await handler.handle(command)

    async def update_stop(self, command: UpdateStopCommand) -> Stop:
        """更新站点

        Args:
            command: 更新站点命令

        Returns:
            Stop: 更新后的站点
        """
        handler = UpdateStopHandler(self._stop_repository)
        return await handler.handle(command)

    async def update_stop_location(self, command: UpdateStopLocationCommand) -> Stop:
        """更新站点位置

        Args:
            command: 更新站点位置命令

        Returns:
            Stop: 更新后的站点
        """
        handler = UpdateStopLocationHandler(self._stop_repository)
        return await handler.handle(command)

    async def update_stop_contact(self, command: UpdateStopContactCommand) -> Stop:
        """更新站点联系人

        Args:
            command: 更新站点联系人命令

        Returns:
            Stop: 更新后的站点
        """
        handler = UpdateStopContactHandler(self._stop_repository)
        return await handler.handle(command)

    async def deactivate_stop(self, command: DeactivateStopCommand) -> Stop:
        """停用站点

        Args:
            command: 停用站点命令

        Returns:
            Stop: 停用后的站点
        """
        handler = DeactivateStopHandler(self._stop_repository)
        return await handler.handle(command)

    async def activate_stop(self, command: ActivateStopCommand) -> Stop:
        """启用站点

        Args:
            command: 启用站点命令

        Returns:
            Stop: 启用后的站点
        """
        handler = ActivateStopHandler(self._stop_repository)
        return await handler.handle(command)

    async def find_nearest_stop(self, latitude: float, longitude: float) -> Optional[Stop]:
        """查找最近的站点

        Args:
            latitude: 纬度
            longitude: 经度

        Returns:
            Optional[Stop]: 最近的站点，如果没有站点则返回None
        """
        from idp.framework.examples.domain.vo.location import Location
        target_location = Location(latitude=latitude, longitude=longitude)
        stops = await self._stop_repository.get_all()
        return self._stop_domain_service.find_nearest_stop(target_location, stops)

    async def validate_stop_sequence(self, stop_ids: List[str]) -> bool:
        """验证站点序列的合理性

        Args:
            stop_ids: 站点ID列表

        Returns:
            bool: 是否合理
        """
        stops = []
        for stop_id in stop_ids:
            stop = await self._stop_repository.get_by_id(stop_id)
            if stop:
                stops.append(stop)
        return self._stop_domain_service.validate_stop_sequence(stops)
