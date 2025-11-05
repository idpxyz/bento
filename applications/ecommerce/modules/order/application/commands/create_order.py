"""Create order command and use case."""

from dataclasses import dataclass
from typing import Any

from applications.ecommerce.modules.order.domain.order import Order
from bento.application.ports import IUnitOfWork
from bento.core.error_codes import CommonErrors
from bento.core.errors import ApplicationException
from bento.core.ids import ID


@dataclass
class OrderItemDTO:
    """Order item data transfer object."""

    product_id: str
    product_name: str
    quantity: int
    unit_price: float


@dataclass
class CreateOrderCommand:
    """Create order command.

    Attributes:
        customer_id: Customer identifier
        items: List of order items
    """

    customer_id: str
    items: list[OrderItemDTO]


class CreateOrderUseCase:
    """Create order use case.

    Handles order creation with validation and persistence.

    Example:
        ```python
        use_case = CreateOrderUseCase(uow)

        command = CreateOrderCommand(
            customer_id="customer-123",
            items=[
                OrderItemDTO(
                    product_id="product-1",
                    product_name="Product A",
                    quantity=2,
                    unit_price=99.99
                )
            ]
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

    async def execute(self, command: CreateOrderCommand) -> dict[str, Any]:
        """Execute create order command.

        Args:
            command: Create order command

        Returns:
            Created order data

        Raises:
            ApplicationException: If validation fails
        """
        # Validate
        if not command.customer_id:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": "customer_id", "reason": "cannot be empty"},
            )

        if not command.items:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": "items", "reason": "must contain at least one item"},
            )

        # Create order
        order_id = ID.generate()
        customer_id = ID(command.customer_id)

        order = Order(
            order_id=order_id,
            customer_id=customer_id,
        )

        # Add items
        for item_dto in command.items:
            order.add_item(
                product_id=ID(item_dto.product_id),
                product_name=item_dto.product_name,
                quantity=item_dto.quantity,
                unit_price=item_dto.unit_price,
            )

        # Persist
        async with self.uow:
            # Get order repository from UoW
            order_repo = self.uow.repository(Order)

            # Save order (automatically tracks aggregate)
            await order_repo.save(order)

            # Commit transaction (automatically collects events and persists to outbox)
            await self.uow.commit()

        return order.to_dict()
