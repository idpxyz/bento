"""Pay order command and use case."""

from dataclasses import dataclass

from bento.application import CommandHandler, command_handler
from bento.application.ports.uow import UnitOfWork
# CommonErrors removed - use DomainException directly
from bento.core.exceptions import ApplicationException

from contexts.ordering.domain.models.order import Order


@dataclass
class PayOrderCommand:
    """Pay order command."""

    order_id: str
    idempotency_key: str | None = None  # For idempotent payment processing


@command_handler
class PayOrderHandler(CommandHandler[PayOrderCommand, Order]):
    """Pay order use case.

    确认订单支付。
    发布 OrderPaid 事件。
    """

    def __init__(self, uow: UnitOfWork) -> None:
        super().__init__(uow)

    async def validate(self, command: PayOrderCommand) -> None:
        """Validate command."""
        if not command.order_id:
            raise ApplicationException(
                reason_code="INVALID_PARAMS",
                details={"field": "order_id", "reason": "cannot be empty"},
            )

    async def handle(self, command: PayOrderCommand) -> Order:
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

        # 确认支付（领域方法会自动发布 OrderPaidEvent）
        try:
            order.confirm_payment()
        except ValueError as e:
            raise ApplicationException(
                reason_code="INVALID_PARAMS",
                details={"reason": str(e)},
            ) from e

        # 保存
        await order_repo.save(order)

        return order
