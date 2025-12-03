"""Ship order command and use case."""

from dataclasses import dataclass

from bento.application import CommandHandler, command_handler
from bento.application.ports.uow import UnitOfWork
from bento.core.error_codes import CommonErrors
from bento.core.errors import ApplicationException

from contexts.ordering.domain.order import Order


@dataclass
class ShipOrderCommand:
    """Ship order command."""

    order_id: str
    tracking_number: str | None = None


@command_handler
class ShipOrderHandler(CommandHandler[ShipOrderCommand, Order]):
    """Ship order use case.

    订单发货。
    发布 OrderShipped 事件。
    """

    def __init__(self, uow: UnitOfWork) -> None:
        super().__init__(uow)

    async def validate(self, command: ShipOrderCommand) -> None:
        """Validate command."""
        if not command.order_id:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": "order_id", "reason": "cannot be empty"},
            )

    async def handle(self, command: ShipOrderCommand) -> Order:
        """Handle command execution."""
        from contexts.ordering.infrastructure.repositories.order_repository_impl import (
            OrderRepository,
        )

        order_repo = OrderRepository(self.uow._session)  # type: ignore

        # 获取订单
        order = await order_repo.get(command.order_id)
        if not order:
            raise ApplicationException(
                error_code=CommonErrors.NOT_FOUND,
                details={"resource": "order", "id": command.order_id},
            )

        # 发货（领域方法会自动发布 OrderShippedEvent）
        try:
            order.ship(tracking_number=command.tracking_number)
        except ValueError as e:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"reason": str(e)},
            ) from e

        # 保存
        await order_repo.save(order)

        return order
