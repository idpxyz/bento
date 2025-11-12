"""Cancel order command and use case."""

from dataclasses import dataclass

from applications.ecommerce.modules.order.domain.order import Order
from applications.ecommerce.modules.order.errors import OrderErrors
from bento.application.ports import IUnitOfWork
from bento.application.usecase import BaseUseCase
from bento.core.error_codes import CommonErrors
from bento.core.errors import ApplicationException
from bento.core.ids import ID


@dataclass
class CancelOrderCommand:
    """Cancel order command.

    Attributes:
        order_id: Order identifier
        reason: Optional cancellation reason
    """

    order_id: str
    reason: str | None = None


class CancelOrderUseCase(BaseUseCase[CancelOrderCommand, Order]):
    """Cancel order use case.

    Handles order cancellation.

    Example:
        ```python
        use_case = CancelOrderUseCase(uow)

        command = CancelOrderCommand(
            order_id="order-123",
            reason="Customer request"
        )
        order = await use_case.execute(command)
        ```
    """

    def __init__(self, uow: IUnitOfWork) -> None:
        super().__init__(uow)

    async def validate(self, command: CancelOrderCommand) -> None:
        if not command.order_id:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": "order_id", "reason": "cannot be empty"},
            )

    async def handle(self, command: CancelOrderCommand) -> Order:
        order_id = ID(command.order_id)
        order_repo = self.uow.repository(Order)

        order = await order_repo.find_by_id(order_id)
        if not order:
            raise ApplicationException(
                error_code=OrderErrors.ORDER_NOT_FOUND, details={"order_id": command.order_id}
            )

        order.cancel(reason=command.reason)
        await order_repo.save(order)
        return order
