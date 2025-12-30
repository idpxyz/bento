"""Order API routes (FastAPI) - Thin Interface Layer"""

from fastapi import APIRouter, Query

from contexts.ordering.application.commands.cancel_order import (
    CancelOrderCommand,
    CancelOrderHandler,
)
from contexts.ordering.application.commands.create_order import (
    CreateOrderCommand,
    CreateOrderHandler,
    OrderItemInput,
)
from contexts.ordering.application.commands.pay_order import (
    PayOrderCommand,
    PayOrderHandler,
)
from contexts.ordering.application.commands.ship_order import (
    ShipOrderCommand,
    ShipOrderHandler,
)
from contexts.ordering.application.queries.get_order import (
    GetOrderHandler,
    GetOrderQuery,
)
from contexts.ordering.application.queries.list_orders import (
    ListOrdersHandler,
    ListOrdersQuery,
)
from contexts.ordering.interfaces.dto import (
    CancelOrderRequest,
    # Request Models
    CreateOrderRequest,
    ListOrdersResponse,
    # Response Models
    OrderResponse,
    PayOrderRequest,
    ShipOrderRequest,
)
from contexts.ordering.interfaces.mappers import order_to_response
from shared.infrastructure.dependencies import handler_dependency

router = APIRouter()


# ==================== Dependency Injection ====================
#
# ==================== API Routes ====================


@router.post(
    "/",
    response_model=OrderResponse,
    status_code=201,
    summary="Create a new order",
)
async def create_order(
    request: CreateOrderRequest,
    handler: CreateOrderHandler = handler_dependency(CreateOrderHandler),
) -> OrderResponse:
    """Create a new order with items.

    Supports idempotency via X-Idempotency-Key HTTP Header.
    If the same key is sent twice, the second request will return
    the cached response from the first request.

    Example:
        curl -X POST /api/v1/orders/ \\
          -H "X-Idempotency-Key: order-20251229-001" \\
          -d '{"customer_id": "cust-001", "items": [...]}'
    """
    # Request → Command
    items = [
        OrderItemInput(
            product_id=item.product_id,
            product_name=item.product_name,
            quantity=item.quantity,
            unit_price=item.unit_price,
        )
        for item in request.items
    ]

    command = CreateOrderCommand(
        customer_id=request.customer_id,
        items=items,
    )

    # Execute Command
    order = await handler.execute(command)

    # Domain → DTO → Response
    return order_to_response(order)


@router.get(
    "/",
    response_model=ListOrdersResponse,
    summary="List orders",
)
async def list_orders(
    handler: ListOrdersHandler = handler_dependency(ListOrdersHandler),
    customer_id: str | None = Query(None, description="Filter by customer ID"),
) -> ListOrdersResponse:
    """List orders with optional customer filter."""
    query = ListOrdersQuery(customer_id=customer_id)

    result = await handler.execute(query)

    return ListOrdersResponse(
        items=[order_to_response(order) for order in result.orders],
        total=result.total,
    )


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    summary="Get an order",
)
async def get_order(
    order_id: str,
    handler: GetOrderHandler = handler_dependency(GetOrderHandler),
) -> OrderResponse:
    """Get an order by ID."""
    query = GetOrderQuery(order_id=order_id)
    order = await handler.execute(query)
    return order_to_response(order)


@router.post(
    "/{order_id}/pay",
    response_model=OrderResponse,
    summary="Pay for an order",
)
async def pay_order(
    order_id: str,
    request: PayOrderRequest,
    handler: PayOrderHandler = handler_dependency(PayOrderHandler),
) -> OrderResponse:
    """Confirm payment for an order.

    Supports idempotency via X-Idempotency-Key HTTP Header to prevent duplicate payments.

    Example:
        curl -X POST /api/v1/orders/{order_id}/pay \\
          -H "X-Idempotency-Key: payment-{order_id}-001"
    """
    command = PayOrderCommand(
        order_id=order_id,
    )
    order = await handler.execute(command)
    return order_to_response(order)


@router.post(
    "/{order_id}/ship",
    response_model=OrderResponse,
    summary="Ship an order",
)
async def ship_order(
    order_id: str,
    request: ShipOrderRequest,
    handler: ShipOrderHandler = handler_dependency(ShipOrderHandler),
) -> OrderResponse:
    """Ship an order.

    Supports idempotency via X-Idempotency-Key HTTP Header to prevent duplicate shipments.

    Example:
        curl -X POST /api/v1/orders/{order_id}/ship \\
          -H "X-Idempotency-Key: shipment-{order_id}-001" \\
          -d '{"tracking_number": "SF123456"}'
    """
    from bento.core.exceptions import ApplicationException
    from fastapi import HTTPException

    try:
        command = ShipOrderCommand(
            order_id=order_id,
            tracking_number=request.tracking_number,
        )
        order = await handler.execute(command)
        return order_to_response(order)
    except ApplicationException as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Order not found") from e
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post(
    "/{order_id}/cancel",
    response_model=OrderResponse,
    summary="Cancel an order",
)
async def cancel_order(
    order_id: str,
    request: CancelOrderRequest,
    handler: CancelOrderHandler = handler_dependency(CancelOrderHandler),
) -> OrderResponse:
    """Cancel an order."""
    command = CancelOrderCommand(
        order_id=order_id,
        reason=request.reason,
    )
    order = await handler.execute(command)
    return order_to_response(order)
