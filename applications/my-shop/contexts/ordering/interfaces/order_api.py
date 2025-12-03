"""Order API routes (FastAPI) - Thin Interface Layer"""

from typing import Annotated, Any

from bento.persistence.uow import SQLAlchemyUnitOfWork
from fastapi import APIRouter, Depends
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
    GetOrderQuery,
    GetOrderHandler,
)
from contexts.ordering.application.queries.list_orders import (
    ListOrdersQuery,
    ListOrdersHandler,
)
from contexts.ordering.interfaces.order_presenters import order_to_dict
from shared.infrastructure.dependencies import get_handler, get_uow

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


class PayOrderRequest(BaseModel):
    """Pay order request model."""

    pass  # 只需要 order_id（从路径获取）


class ShipOrderRequest(BaseModel):
    """Ship order request model."""

    tracking_number: str | None = None


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
    created_at: str | None
    paid_at: str | None
    shipped_at: str | None


class ListOrdersResponse(BaseModel):
    """List orders response model."""

    items: list[OrderResponse]
    total: int


# ==================== Dependency Injection ====================
#
# Note: Most Handlers use the universal get_handler() factory.
# CreateOrderHandler is special because it needs ProductCatalogAdapter.
#


async def get_create_order_handler(
    uow: SQLAlchemyUnitOfWork = Depends(get_uow),
) -> CreateOrderHandler:
    """Factory for CreateOrderHandler (needs ProductCatalogAdapter)."""
    from contexts.ordering.infrastructure.adapters.services.product_catalog_adapter import (
        ProductCatalogAdapter,
    )

    # 创建反腐败层适配器
    product_catalog = ProductCatalogAdapter(uow.session)
    return CreateOrderHandler(uow, product_catalog)


# ==================== API Routes ====================


@router.post(
    "/",
    response_model=OrderResponse,
    status_code=201,
    summary="Create a new order",
)
async def create_order(
    request: CreateOrderRequest,
    handler: Annotated[CreateOrderHandler, Depends(get_create_order_handler)],
) -> dict[str, Any]:
    """Create a new order with items."""
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
    handler: Annotated[ListOrdersHandler, Depends(get_handler)],
    customer_id: str | None = None,
) -> dict[str, Any]:
    """List orders with optional customer filter."""
    query = ListOrdersQuery(customer_id=customer_id)

    result = await handler.execute(query)

    return {
        "items": [order_to_dict(order) for order in result.orders],
        "total": result.total,
    }


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    summary="Get an order",
)
async def get_order(
    order_id: str,
    handler: Annotated[GetOrderHandler, Depends(get_handler)],
) -> dict[str, Any]:
    """Get an order by ID."""
    query = GetOrderQuery(order_id=order_id)
    order = await handler.execute(query)
    return order_to_dict(order)


@router.post(
    "/{order_id}/pay",
    response_model=OrderResponse,
    summary="Pay for an order",
)
async def pay_order(
    order_id: str,
    handler: Annotated[PayOrderHandler, Depends(get_handler)],
) -> dict[str, Any]:
    """Confirm payment for an order."""
    command = PayOrderCommand(order_id=order_id)
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
    handler: Annotated[ShipOrderHandler, Depends(get_handler)],
) -> dict[str, Any]:
    """Ship an order."""
    from bento.core.errors import ApplicationException
    from fastapi import HTTPException

    try:
        command = ShipOrderCommand(
            order_id=order_id,
            tracking_number=request.tracking_number,
        )
        order = await handler.execute(command)
        return order_to_dict(order)
    except ApplicationException as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Order not found") from None
        raise HTTPException(status_code=400, detail=str(e)) from None


@router.post(
    "/{order_id}/cancel",
    response_model=OrderResponse,
    summary="Cancel an order",
)
async def cancel_order(
    order_id: str,
    request: CancelOrderRequest,
    handler: Annotated[CancelOrderHandler, Depends(get_handler)],
) -> dict[str, Any]:
    """Cancel an order."""
    command = CancelOrderCommand(
        order_id=order_id,
        reason=request.reason,
    )
    order = await handler.execute(command)
    return order_to_dict(order)
