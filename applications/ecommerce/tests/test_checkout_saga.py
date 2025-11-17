import pytest

from applications.ecommerce.modules.checkout.application.checkout_order import (
    CheckoutItemDTO,
    CheckoutOrderCommand,
    CheckoutOrderUseCase,
)
from applications.ecommerce.modules.inventory.integration.provider import (
    InMemoryInventoryProvider,
)
from applications.ecommerce.modules.order.domain.order_status import OrderStatus
from applications.ecommerce.modules.payment.integration.gateway import (
    FakePaymentGateway,
)
from applications.ecommerce.runtime.composition import get_unit_of_work


@pytest.mark.asyncio
async def test_checkout_success():
    inv = InMemoryInventoryProvider()
    inv.set_stock("SKU-OK", available=10)
    pg = FakePaymentGateway(default_success=True)

    uow = await get_unit_of_work()
    uc = CheckoutOrderUseCase(uow, inventory=inv, payment=pg)

    cmd = CheckoutOrderCommand(
        customer_id="CUST-1",
        items=[
            CheckoutItemDTO(
                product_id="SKU-OK",
                product_name="P",
                quantity=2,
                unit_price=5.0,
            )
        ],
        currency="USD",
    )

    order = await uc.execute(cmd)

    assert order.status == OrderStatus.PAID
    assert order.items_count == 1


@pytest.mark.asyncio
async def test_checkout_insufficient_stock():
    inv = InMemoryInventoryProvider()
    inv.set_stock("SKU-NO", available=0)
    pg = FakePaymentGateway(default_success=True)

    uow = await get_unit_of_work()
    uc = CheckoutOrderUseCase(uow, inventory=inv, payment=pg)

    cmd = CheckoutOrderCommand(
        customer_id="CUST-2",
        items=[
            CheckoutItemDTO(
                product_id="SKU-NO",
                product_name="P",
                quantity=1,
                unit_price=9.9,
            )
        ],
        currency="USD",
    )

    order = await uc.execute(cmd)

    assert order.status == OrderStatus.CANCELLED


@pytest.mark.asyncio
async def test_checkout_payment_failed_compensates_inventory():
    inv = InMemoryInventoryProvider()
    inv.set_stock("SKU-PAY-FAIL", available=3)
    pg = FakePaymentGateway(default_success=False)

    uow = await get_unit_of_work()
    uc = CheckoutOrderUseCase(uow, inventory=inv, payment=pg)

    cmd = CheckoutOrderCommand(
        customer_id="CUST-3",
        items=[
            CheckoutItemDTO(
                product_id="SKU-PAY-FAIL",
                product_name="P",
                quantity=2,
                unit_price=15.0,
            )
        ],
        currency="USD",
    )

    # capture before
    before = inv._stock["SKU-PAY-FAIL"]["available"]

    order = await uc.execute(cmd)

    # Should be cancelled and inventory released
    assert order.status == OrderStatus.CANCELLED
    assert inv._stock["SKU-PAY-FAIL"]["available"] == before
