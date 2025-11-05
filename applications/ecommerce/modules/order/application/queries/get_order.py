"""Get order query and use case."""

from dataclasses import dataclass
from typing import Any

from applications.ecommerce.modules.order.domain.order import Order
from applications.ecommerce.modules.order.errors import OrderErrors
from bento.application.ports import IUnitOfWork
from bento.core.error_codes import CommonErrors
from bento.core.errors import ApplicationException
from bento.core.ids import ID


@dataclass
class GetOrderQuery:
    """Get order query.

    Attributes:
        order_id: Order identifier
    """

    order_id: str


class GetOrderUseCase:
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
        """Initialize use case.

        Args:
            uow: Unit of work for data access
        """
        self.uow = uow

    async def execute(self, query: GetOrderQuery) -> dict[str, Any]:
        """Execute get order query.

        Args:
            query: Get order query

        Returns:
            Order data

        Raises:
            ApplicationException: If order not found
        """
        # Validate
        if not query.order_id:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": "order_id", "reason": "cannot be empty"},
            )

        order_id = ID(query.order_id)

        async with self.uow:
            # Get order repository from UoW
            order_repo = self.uow.repository(Order)

            # Find order (using find_by_id for consistency with other use cases)
            order = await order_repo.find_by_id(order_id)
            if not order:
                raise ApplicationException(
                    error_code=OrderErrors.ORDER_NOT_FOUND, details={"order_id": query.order_id}
                )

        return order.to_dict()
