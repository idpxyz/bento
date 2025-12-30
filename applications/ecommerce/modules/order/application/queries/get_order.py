"""Get order query and use case."""

from dataclasses import dataclass

from bento.application.usecase import BaseUseCase
from bento.core.error_codes import CommonErrors
from bento.core.errors import ApplicationException

from applications.ecommerce.modules.order.domain.order import Order
from applications.ecommerce.modules.order.errors import OrderErrors
from bento.application.ports import IUnitOfWork
from bento.core.ids import ID


@dataclass
class GetOrderQuery:
    """Get order query.

    Attributes:
        order_id: Order identifier
    """

    order_id: str


class GetOrderUseCase(BaseUseCase[GetOrderQuery, Order]):
    """Get order use case.

    Retrieves an order by ID.

    Example:
        ```python
        use_case = GetOrderUseCase(uow)

        query = GetOrderQuery(order_id="order-123")
        order = await use_case.execute(query)
        ```
    """

    def __init__(self, uow: IUnitOfWork) -> None:
        super().__init__(uow)

    async def validate(self, query: GetOrderQuery) -> None:
        if not query.order_id:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": "order_id", "reason": "cannot be empty"},
            )

    async def handle(self, query: GetOrderQuery) -> Order:
        order_id = ID(query.order_id)
        order_repo = self.uow.repository(Order)

        # Use repository.get which handles ID.value correctly
        order = await order_repo.get(order_id)
        if not order:
            raise ApplicationException(
                error_code=OrderErrors.ORDER_NOT_FOUND, details={"order_id": query.order_id}
            )

        return order
