"""站点相关的命令处理器"""
from idp.framework.application.command.handler import CommandHandler
from idp.framework.examples.application.command.stop import (
    ActivateStopCommand,
    CreateStopCommand,
    DeactivateStopCommand,
    UpdateStopCommand,
    UpdateStopContactCommand,
    UpdateStopLocationCommand,
)
from idp.framework.examples.domain.entity.stop import Stop
from idp.framework.examples.domain.id_generator import IdGenerator
from idp.framework.examples.infrastructure.id_generator import UuidIdGenerator
from idp.framework.examples.infrastructure.persistence.repository.stop import (
    SqlAlchemyStopRepository,
)
from idp.framework.infrastructure.persistence.sqlalchemy.uow import SqlAlchemyAsyncUoW


class CreateStopHandler(CommandHandler[CreateStopCommand, Stop]):
    """创建站点命令处理器"""

    def __init__(self, uow: SqlAlchemyAsyncUoW):
        """初始化

        Args:
            uow: 工作单元
        """
        self._uow = uow
        self._id_generator = UuidIdGenerator()
        self._repository = SqlAlchemyStopRepository(uow, self._id_generator)

    async def handle(self, command: CreateStopCommand) -> Stop:
        """处理创建站点命令

        Args:
            command: 创建站点命令

        Returns:
            Stop: 创建的站点
        """
        stop = Stop.create(
            name=command.name,
            address=command.address,
            location=command.location,
            contact=command.contact,
            description=command.description,
            tenant_id=command.tenant_id,
            id_generator=self._id_generator
        )

        try:
            saved_stop = await self._repository.save(stop)
            await self._uow.session.commit()
            return saved_stop
        except Exception as e:
            raise e


class UpdateStopHandler(CommandHandler[UpdateStopCommand, Stop]):
    """更新站点命令处理器"""

    def __init__(self, uow: SqlAlchemyAsyncUoW):
        """初始化

        Args:
            uow: 工作单元
        """
        self._uow = uow
        self._id_generator = UuidIdGenerator()
        self._repository = SqlAlchemyStopRepository(uow, self._id_generator)

    async def handle(self, command: UpdateStopCommand) -> Stop:
        """处理更新站点命令

        Args:
            command: 更新站点命令

        Returns:
            Stop: 更新后的站点
        """
        try:
            existing_stop = await self._repository.get_by_id(command.stop_id)
            if not existing_stop:
                raise ValueError(f"站点 {command.stop_id} 不存在")

            # 创建新的站点实例，保留原有ID
            updated_stop = Stop(
                name=command.name,
                address=command.address,
                location=command.location,
                contact=command.contact,
                description=command.description,
                is_active=command.is_active
            )
            updated_stop.tenant_id = command.tenant_id
            updated_stop.id = command.stop_id

            saved_stop = await self._repository.save(updated_stop)
            await self._uow.session.commit()
            return saved_stop
        except Exception as e:
            raise e


class UpdateStopLocationHandler(CommandHandler[UpdateStopLocationCommand, Stop]):
    """更新站点位置命令处理器"""

    def __init__(self, uow: SqlAlchemyAsyncUoW):
        """初始化

        Args:
            uow: 工作单元
        """
        self._uow = uow
        self._id_generator = UuidIdGenerator()
        self._repository = SqlAlchemyStopRepository(uow, self._id_generator)

    async def handle(self, command: UpdateStopLocationCommand) -> Stop:
        """处理更新站点位置命令

        Args:
            command: 更新站点位置命令

        Returns:
            Stop: 更新后的站点
        """
        try:
            existing_stop = await self._repository.get_by_id(command.stop_id)
            if not existing_stop:
                raise ValueError(f"站点 {command.stop_id} 不存在")

            updated_stop = existing_stop.update_location(command.location)

            saved_stop = await self._repository.save(updated_stop)
            await self._uow.session.commit()
            return saved_stop
        except Exception as e:
            raise e


class UpdateStopContactHandler(CommandHandler[UpdateStopContactCommand, Stop]):
    """更新站点联系人命令处理器"""

    def __init__(self, uow: SqlAlchemyAsyncUoW):
        """初始化

        Args:
            uow: 工作单元
        """
        self._uow = uow
        self._id_generator = UuidIdGenerator()
        self._repository = SqlAlchemyStopRepository(uow, self._id_generator)

    async def handle(self, command: UpdateStopContactCommand) -> Stop:
        """处理更新站点联系人命令

        Args:
            command: 更新站点联系人命令

        Returns:
            Stop: 更新后的站点
        """
        try:
            existing_stop = await self._repository.get_by_id(command.stop_id)
            if not existing_stop:
                raise ValueError(f"站点 {command.stop_id} 不存在")

            updated_stop = existing_stop.update_contact(command.contact)

            saved_stop = await self._repository.save(updated_stop)
            await self._uow.session.commit()
            return saved_stop
        except Exception as e:
            raise e


class DeactivateStopHandler(CommandHandler[DeactivateStopCommand, Stop]):
    """停用站点命令处理器"""

    def __init__(self, uow: SqlAlchemyAsyncUoW):
        """初始化

        Args:
            uow: 工作单元
        """
        self._uow = uow
        self._id_generator = UuidIdGenerator()
        self._repository = SqlAlchemyStopRepository(uow, self._id_generator)

    async def handle(self, command: DeactivateStopCommand) -> Stop:
        """处理停用站点命令

        Args:
            command: 停用站点命令

        Returns:
            Stop: 停用后的站点
        """
        try:
            existing_stop = await self._repository.get_by_id(command.stop_id)
            if not existing_stop:
                raise ValueError(f"站点 {command.stop_id} 不存在")

            updated_stop = existing_stop.deactivate()

            saved_stop = await self._repository.save(updated_stop)
            await self._uow.session.commit()
            return saved_stop
        except Exception as e:
            raise e


class ActivateStopHandler(CommandHandler[ActivateStopCommand, Stop]):
    """激活站点命令处理器"""

    def __init__(self, uow: SqlAlchemyAsyncUoW):
        """初始化

        Args:
            uow: 工作单元
        """
        self._uow = uow
        self._id_generator = UuidIdGenerator()
        self._repository = SqlAlchemyStopRepository(uow, self._id_generator)

    async def handle(self, command: ActivateStopCommand) -> Stop:
        """处理激活站点命令

        Args:
            command: 激活站点命令

        Returns:
            Stop: 激活后的站点
        """
        try:
            existing_stop = await self._repository.get_by_id(command.stop_id)
            if not existing_stop:
                raise ValueError(f"站点 {command.stop_id} 不存在")

            updated_stop = existing_stop.activate()

            saved_stop = await self._repository.save(updated_stop)
            await self._uow.session.commit()
            return saved_stop
        except Exception as e:
            raise e
