"""Checkout Saga use case.

Flow (minimal):
1) Create Order (pending)
2) Reserve inventory via InventoryProvider
3) Authorize payment via PaymentGateway
4) If payment authorized -> order.pay()
   Else -> release reservation and order.cancel()

Note: This is a simplified single-transaction orchestration for demo/tests.
"""

from __future__ import annotations

from dataclasses import dataclass

from bento.application.usecase import BaseUseCase
from bento.core.error_codes import CommonErrors
from bento.core.errors import ApplicationException

from applications.ecommerce.modules.inventory.integration.provider import (
    InMemoryInventoryProvider,
    InventoryProvider,
    ReserveItem,
)
from applications.ecommerce.modules.order.domain.order import Order
from applications.ecommerce.modules.payment.integration.gateway import (
    FakePaymentGateway,
    PaymentAuthorizationRequest,
    PaymentGateway,
)
from bento.application.ports import IUnitOfWork
from bento.core.ids import ID


@dataclass
class CheckoutItemDTO:
    product_id: str
    product_name: str
    quantity: int
    unit_price: float


@dataclass
class CheckoutOrderCommand:
    customer_id: str
    items: list[CheckoutItemDTO]
    currency: str = "USD"


class CheckoutOrderUseCase(BaseUseCase[CheckoutOrderCommand, Order]):
    def __init__(
        self,
        uow: IUnitOfWork,
        inventory: InventoryProvider | None = None,
        payment: PaymentGateway | None = None,
    ) -> None:
        super().__init__(uow)
        # Allow injecting fakes or real providers
        self.inventory: InventoryProvider = inventory or InMemoryInventoryProvider()
        self.payment: PaymentGateway = payment or FakePaymentGateway()

    async def validate(self, command: CheckoutOrderCommand) -> None:
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

    async def handle(self, command: CheckoutOrderCommand) -> Order:
        # 1) Create order pending
        order_id = ID.generate()
        customer_id = ID(command.customer_id)
        order = Order(order_id=order_id, customer_id=customer_id)
        order.currency = command.currency

        for item in command.items:
            order.add_item(
                product_id=ID(item.product_id),
                product_name=item.product_name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                currency=command.currency,
            )

        order_repo = self.uow.repository(Order)
        await order_repo.save(order)

        # 2) Reserve inventory
        reserve_items = [
            ReserveItem(product_id=i.product_id, quantity=i.quantity) for i in command.items
        ]
        reserve_res = await self.inventory.reserve(
            order_id=order.id.value,
            customer_id=command.customer_id,
            items=reserve_items,
        )
        if not reserve_res.success:
            order.cancel(reason=reserve_res.reason or "insufficient_stock")
            await order_repo.save(order)
            return order

        # 3) Authorize payment
        pay_req = PaymentAuthorizationRequest(
            order_id=order.id.value,
            customer_id=command.customer_id,
            amount=order.total_amount,
            currency=command.currency,
            method="card",
        )
        pay_res = await self.payment.authorize(pay_req)

        if not pay_res.authorized:
            # compensation: release inventory and cancel order
            await self.inventory.release(order_id=order.id.value)
            order.cancel(reason=pay_res.failure_reason or "payment_failed")
            await order_repo.save(order)
            return order

        # 4) Confirm order (paid)
        order.pay()
        await order_repo.save(order)
        return order
