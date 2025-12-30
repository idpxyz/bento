"""Pay order command and use case."""

from dataclasses import dataclass

from bento.application.usecase import BaseUseCase
from bento.core.error_codes import CommonErrors
from bento.core.errors import ApplicationException

from applications.ecommerce.modules.order.domain.order import Order
from applications.ecommerce.modules.order.errors import OrderErrors
from bento.application.ports import IUnitOfWork
from bento.core.ids import ID


@dataclass
class PayOrderCommand:
    """Pay order command.

    Attributes:
        order_id: Order identifier
    """

    order_id: str


class PayOrderUseCase(BaseUseCase[PayOrderCommand, Order]):
    """Pay order use case.

    Handles order payment processing.

    Example:
        ```python
        use_case = PayOrderUseCase(uow)

        command = PayOrderCommand(order_id="order-123")
        order = await use_case.execute(command)
        ```
    """

    def __init__(self, uow: IUnitOfWork) -> None:
        super().__init__(uow)

    async def validate(self, command: PayOrderCommand) -> None:
        if not command.order_id:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": "order_id", "reason": "cannot be empty"},
            )

    async def handle(self, command: PayOrderCommand) -> Order:
        order_id = ID(command.order_id)
        order_repo = self.uow.repository(Order)

        order = await order_repo.find_by_id(order_id)
        if not order:
            raise ApplicationException(
                error_code=OrderErrors.ORDER_NOT_FOUND, details={"order_id": command.order_id}
            )

        order.pay()
        await order_repo.save(order)
        return order
