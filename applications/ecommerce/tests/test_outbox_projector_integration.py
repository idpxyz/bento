import pytest

from applications.ecommerce.modules.order.application.commands.create_order import (
    CreateOrderCommand,
    CreateOrderUseCase,
    OrderItemDTO,
)
from applications.ecommerce.runtime.composition import get_unit_of_work
from applications.ecommerce.runtime.jobs import publish_all_once


@pytest.mark.asyncio
async def test_outbox_projector_publishes_order_events(caplog):
    # Arrange
    caplog.set_level("INFO")
    uow = await get_unit_of_work()
    use_case = CreateOrderUseCase(uow)

    cmd = CreateOrderCommand(
        customer_id="customer-int-1",
        items=[
            OrderItemDTO(
                product_id="SKU-001",
                product_name="Test Product",
                quantity=1,
                unit_price=19.99,
            )
        ],
    )

    # Act: create order (events persisted to Outbox on commit)
    await use_case.execute(cmd)

    # Act: publish pending outbox events via projector
    processed = await publish_all_once()

    # Assert: at least one event processed
    assert processed > 0

    # Assert: logs indicate publish and handler execution
    text = caplog.text
    assert (
        "Publishing event: OrderCreated" in text
        or "Finished processing OrderCreated" in text
        or "Order created:" in text
    )
