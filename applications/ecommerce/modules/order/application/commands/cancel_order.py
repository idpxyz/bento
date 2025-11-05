"""Cancel order command and use case."""

from dataclasses import dataclass
from typing import Any

from applications.ecommerce.modules.order.domain.order import Order
from applications.ecommerce.modules.order.errors import OrderErrors
from bento.application.ports import IUnitOfWork
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


class CancelOrderUseCase:
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
        """Initialize use case.

        Args:
            uow: Unit of work for transaction management
        """
        self.uow = uow

    async def execute(self, command: CancelOrderCommand) -> dict[str, Any]:
        """Execute cancel order command.

        Args:
            command: Cancel order command

        Returns:
            Updated order data

        Raises:
            ApplicationException: If order not found
        """
        # Validate
        if not command.order_id:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": "order_id", "reason": "cannot be empty"},
            )

        order_id = ID(command.order_id)

        async with self.uow:
            # Get order repository from UoW
            order_repo = self.uow.repository(Order)

            # Find order
            order = await order_repo.find_by_id(order_id)
            if not order:
                raise ApplicationException(
                    error_code=OrderErrors.ORDER_NOT_FOUND, details={"order_id": command.order_id}
                )

            # Cancel order (domain logic)
            order.cancel(reason=command.reason)

            # Save order (automatically tracks aggregate)
            await order_repo.save(order)

            # Commit transaction (automatically collects events and persists to outbox)
            await self.uow.commit()

        return order.to_dict()
