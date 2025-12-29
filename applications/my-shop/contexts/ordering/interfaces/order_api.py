"""Order API routes (FastAPI) - Thin Interface Layer"""

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter
from pydantic import BaseModel

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
from contexts.ordering.interfaces.order_presenters import order_to_dict
from shared.infrastructure.dependencies import handler_dependency

router = APIRouter()


# ==================== Request/Response Models ====================


class OrderItemRequest(BaseModel):
    """Order item request model."""

    product_id: str
    product_name: str
    quantity: int
    unit_price: float


class CreateOrderRequest(BaseModel):
    """Create order request model."""

    customer_id: str
    items: list[OrderItemRequest]
    idempotency_key: str | None = None  # For idempotent order creation


class PayOrderRequest(BaseModel):
    """Pay order request model."""

    idempotency_key: str | None = None  # For idempotent payment processing


class ShipOrderRequest(BaseModel):
    """Ship order request model."""

    tracking_number: str | None = None
    idempotency_key: str | None = None  # For idempotent shipping


class CancelOrderRequest(BaseModel):
    """Cancel order request model."""

    reason: str


class OrderItemResponse(BaseModel):
    """Order item response model."""

    id: str
    product_id: str
    product_name: str
    quantity: int
    unit_price: float
    subtotal: float


class OrderResponse(BaseModel):
    """Order response model."""

    id: str
    customer_id: str
    items: list[OrderItemResponse]
    total: float
    status: str
    created_at: datetime | None  # ✅ 与 OrderDTO 保持一致
    paid_at: datetime | None
    shipped_at: datetime | None


class ListOrdersResponse(BaseModel):
    """List orders response model."""

    items: list[OrderResponse]
    total: int


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
    handler: Annotated[CreateOrderHandler, handler_dependency(CreateOrderHandler)],
) -> dict[str, Any]:
    """Create a new order with items.

    Supports idempotency via idempotency_key field.
    If the same idempotency_key is sent twice, the second request will return
    the same order that was created by the first request.
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
        idempotency_key=request.idempotency_key,
    )

    # Execute Use Case
    order = await handler.execute(command)

    # Domain → Response
    return order_to_dict(order)


@router.get(
    "/",
    response_model=ListOrdersResponse,
    summary="List orders",
)
async def list_orders(
    handler: Annotated[ListOrdersHandler, handler_dependency(ListOrdersHandler)],
    customer_id: str | None = None,
) -> dict[str, Any]:
    """List orders with optional customer filter."""
    query = ListOrdersQuery(customer_id=customer_id)

    result = await handler.execute(query)

    return {
        "items": [order.model_dump() for order in result.orders],  # ✅ 使用 DTO 内置序列化
        "total": result.total,
    }


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    summary="Get an order",
)
async def get_order(
    order_id: str,
    handler: Annotated[GetOrderHandler, handler_dependency(GetOrderHandler)],
) -> dict[str, Any]:
    """Get an order by ID."""
    query = GetOrderQuery(order_id=order_id)
    order = await handler.execute(query)  # 返回 OrderDTO
    return order.model_dump()  # ✅ 使用 DTO 内置序列化


@router.post(
    "/{order_id}/pay",
    response_model=OrderResponse,
    summary="Pay for an order",
)
async def pay_order(
    order_id: str,
    request: PayOrderRequest,
    handler: Annotated[PayOrderHandler, handler_dependency(PayOrderHandler)],
) -> dict[str, Any]:
    """Confirm payment for an order.

    Supports idempotency via idempotency_key field to prevent duplicate payments.
    """
    command = PayOrderCommand(
        order_id=order_id,
        idempotency_key=request.idempotency_key,
    )
    order = await handler.execute(command)
    return order_to_dict(order)


@router.post(
    "/{order_id}/ship",
    response_model=OrderResponse,
    summary="Ship an order",
)
async def ship_order(
    order_id: str,
    request: ShipOrderRequest,
    handler: Annotated[ShipOrderHandler, handler_dependency(ShipOrderHandler)],
) -> dict[str, Any]:
    """Ship an order.

    Supports idempotency via idempotency_key field to prevent duplicate shipments.
    """
    from bento.core.exceptions import ApplicationException
    from fastapi import HTTPException

    try:
        command = ShipOrderCommand(
            order_id=order_id,
            tracking_number=request.tracking_number,
            idempotency_key=request.idempotency_key,
        )
        order = await handler.execute(command)
        return order_to_dict(order)
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
    handler: Annotated[CancelOrderHandler, handler_dependency(CancelOrderHandler)],
) -> dict[str, Any]:
    """Cancel an order."""
    command = CancelOrderCommand(
        order_id=order_id,
        reason=request.reason,
    )
    order = await handler.execute(command)
    return order_to_dict(order)
