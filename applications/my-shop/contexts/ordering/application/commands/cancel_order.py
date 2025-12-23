"""Cancel order command and use case."""

from dataclasses import dataclass

from bento.application import CommandHandler, command_handler
from bento.application.ports.uow import UnitOfWork
# CommonErrors removed - use DomainException directly
from bento.core.exceptions import ApplicationException

from contexts.ordering.domain.models.order import Order


@dataclass
class CancelOrderCommand:
    """Cancel order command."""

    order_id: str
    reason: str


@command_handler
class CancelOrderHandler(CommandHandler[CancelOrderCommand, Order]):
    """Cancel order use case.

    取消订单。
    发布 OrderCancelled 事件。
    """

    def __init__(self, uow: UnitOfWork) -> None:
        super().__init__(uow)

    async def validate(self, command: CancelOrderCommand) -> None:
        """Validate command."""
        if not command.order_id:
            raise ApplicationException(
                reason_code="INVALID_PARAMS",
                details={"field": "order_id", "reason": "cannot be empty"},
            )
        if not command.reason:
            raise ApplicationException(
                reason_code="INVALID_PARAMS",
                details={"field": "reason", "reason": "cannot be empty"},
            )

    async def handle(self, command: CancelOrderCommand) -> Order:
        """Handle command execution."""
        from contexts.ordering.infrastructure.repositories.order_repository_impl import (
            OrderRepository,
        )

        order_repo = OrderRepository(self.uow._session)  # type: ignore

        # 获取订单
        order = await order_repo.get(command.order_id)
        if not order:
            raise ApplicationException(
                reason_code="NOT_FOUND",
                details={"resource": "order", "id": command.order_id},
            )

        # 取消订单（领域方法会自动发布 OrderCancelledEvent）
        try:
            order.cancel(reason=command.reason)
        except ValueError as e:
            raise ApplicationException(
                reason_code="INVALID_PARAMS",
                details={"reason": str(e)},
            ) from e
        # 保存
        await order_repo.save(order)

        return order
