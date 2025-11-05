"""Order API routes (FastAPI)."""

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from bento.core.error_handler import get_error_responses_schema
from applications.ecommerce.modules.order.application import (
    CreateOrderCommand,
    CreateOrderUseCase,
    PayOrderCommand,
    PayOrderUseCase,
    CancelOrderCommand,
    CancelOrderUseCase,
    GetOrderQuery,
    GetOrderUseCase,
    OrderItemDTO,
)

# Create router
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
    """Pay order request model (empty for now)."""
    pass


class CancelOrderRequest(BaseModel):
    """Cancel order request model."""
    
    reason: str | None = None


# ==================== Dependency Injection ====================


async def get_create_order_use_case() -> CreateOrderUseCase:
    """Get create order use case (dependency).
    
    In a real application, this would get the UoW from a DI container.
    For now, this is a placeholder that will be implemented in bootstrap.
    """
    from applications.ecommerce.runtime.composition import get_unit_of_work
    
    uow = await get_unit_of_work()
    return CreateOrderUseCase(uow)


async def get_pay_order_use_case() -> PayOrderUseCase:
    """Get pay order use case (dependency)."""
    from applications.ecommerce.runtime.composition import get_unit_of_work
    
    uow = await get_unit_of_work()
    return PayOrderUseCase(uow)


async def get_cancel_order_use_case() -> CancelOrderUseCase:
    """Get cancel order use case (dependency)."""
    from applications.ecommerce.runtime.composition import get_unit_of_work
    
    uow = await get_unit_of_work()
    return CancelOrderUseCase(uow)


async def get_get_order_use_case() -> GetOrderUseCase:
    """Get get order use case (dependency)."""
    from applications.ecommerce.runtime.composition import get_unit_of_work
    
    uow = await get_unit_of_work()
    return GetOrderUseCase(uow)


# ==================== API Routes ====================


@router.post(
    "",
    response_model=dict[str, Any],
    responses=get_error_responses_schema(),
    summary="Create a new order",
    description="Create a new order with items",
)
async def create_order(
    request: CreateOrderRequest,
    use_case: CreateOrderUseCase = Depends(get_create_order_use_case),
) -> dict[str, Any]:
    """Create a new order.
    
    Args:
        request: Create order request
        use_case: Create order use case (injected)
        
    Returns:
        Created order data
    """
    # Convert request to command
    items = [
        OrderItemDTO(
            product_id=item.product_id,
            product_name=item.product_name,
            quantity=item.quantity,
            unit_price=item.unit_price,
            subtotal=item.quantity * item.unit_price,  # Calculate subtotal
        )
        for item in request.items
    ]
    
    command = CreateOrderCommand(
        customer_id=request.customer_id,
        items=items,
    )
    
    # Execute use case
    order = await use_case.execute(command)
    
    return order


@router.get(
    "/{order_id}",
    response_model=dict[str, Any],
    responses=get_error_responses_schema(),
    summary="Get an order",
    description="Retrieve an order by ID",
)
async def get_order(
    order_id: str,
    use_case: GetOrderUseCase = Depends(get_get_order_use_case),
) -> dict[str, Any]:
    """Get an order by ID.
    
    Args:
        order_id: Order identifier
        use_case: Get order use case (injected)
        
    Returns:
        Order data
    """
    query = GetOrderQuery(order_id=order_id)
    order = await use_case.execute(query)
    return order


@router.post(
    "/{order_id}/pay",
    response_model=dict[str, Any],
    responses=get_error_responses_schema(),
    summary="Pay for an order",
    description="Mark an order as paid",
)
async def pay_order(
    order_id: str,
    request: PayOrderRequest,
    use_case: PayOrderUseCase = Depends(get_pay_order_use_case),
) -> dict[str, Any]:
    """Pay for an order.
    
    Args:
        order_id: Order identifier
        request: Pay order request
        use_case: Pay order use case (injected)
        
    Returns:
        Updated order data
    """
    command = PayOrderCommand(order_id=order_id)
    order = await use_case.execute(command)
    return order


@router.post(
    "/{order_id}/cancel",
    response_model=dict[str, Any],
    responses=get_error_responses_schema(),
    summary="Cancel an order",
    description="Cancel a pending order",
)
async def cancel_order(
    order_id: str,
    request: CancelOrderRequest,
    use_case: CancelOrderUseCase = Depends(get_cancel_order_use_case),
) -> dict[str, Any]:
    """Cancel an order.
    
    Args:
        order_id: Order identifier
        request: Cancel order request
        use_case: Cancel order use case (injected)
        
    Returns:
        Updated order data
    """
    command = CancelOrderCommand(
        order_id=order_id,
        reason=request.reason,
    )
    order = await use_case.execute(command)
    return order

