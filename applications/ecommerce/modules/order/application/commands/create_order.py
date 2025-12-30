"""Create order command and use case."""

from dataclasses import dataclass

from bento.application.usecase import BaseUseCase
from bento.core.error_codes import CommonErrors
from bento.core.errors import ApplicationException

from applications.ecommerce.modules.order.domain.events import OrderCreated
from applications.ecommerce.modules.order.domain.order import Order
from bento.application.ports import IUnitOfWork
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


class CreateOrderUseCase(BaseUseCase[CreateOrderCommand, Order]):
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
        super().__init__(uow)

    async def validate(self, command: CreateOrderCommand) -> None:
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

    async def handle(self, command: CreateOrderCommand) -> Order:
        order_id = ID.generate()
        customer_id = ID(command.customer_id)

        order = Order(order_id=order_id, customer_id=customer_id)

        for item_dto in command.items:
            order.add_item(
                product_id=ID(item_dto.product_id),
                product_name=item_dto.product_name,
                quantity=item_dto.quantity,
                unit_price=item_dto.unit_price,
            )

        # Publish OrderCreated event after items are added (ensures correct total)
        order.add_event(
            OrderCreated(
                order_id=ID(order.id.value),
                customer_id=order.customer_id,
                total_amount=order.total_amount,
            )
        )

        # Persist via repository inside UoW
        order_repo = self.uow.repository(Order)
        await order_repo.save(order)
        return order
