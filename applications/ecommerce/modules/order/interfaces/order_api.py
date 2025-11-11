"""Order API routes (FastAPI)."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from applications.ecommerce.modules.order.application import (
    CancelOrderCommand,
    CancelOrderUseCase,
    CreateOrderCommand,
    CreateOrderUseCase,
    GetOrderQuery,
    GetOrderUseCase,
    PayOrderCommand,
    PayOrderUseCase,
)
from applications.ecommerce.modules.order.application.commands.create_order import (
    OrderItemDTO as CreateOrderItemDTO,
)
from applications.ecommerce.modules.order.application.queries.order_query_service import (
    OrderQueryService,
)
from bento.core.error_handler import get_error_responses_schema

# Create router
router = APIRouter()
# 注：UseCase 已统一继承 BaseUseCase（校验 + UoW 事务 + 事件发布）


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


async def get_order_query_service():
    """Provide OrderQueryService with managed session lifecycle."""
    from applications.ecommerce.runtime.composition import get_session

    session_gen = get_session()
    session = await anext(session_gen)
    try:
        yield OrderQueryService(session)
    finally:
        await anext(session_gen, None)


# ==================== API Routes ====================


@router.post(
    "",
    response_model=dict[str, Any],
    responses=get_error_responses_schema(),  # type: ignore[arg-type]
    summary="Create a new order",
    description="Create a new order with items",
)
async def create_order(
    request: CreateOrderRequest,
    use_case: Annotated[CreateOrderUseCase, Depends(get_create_order_use_case)],
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
        CreateOrderItemDTO(
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

    # Execute use case
    order = await use_case.execute(command)

    return order


@router.get(
    "",
    response_model=dict[str, Any],
    responses=get_error_responses_schema(),  # type: ignore[arg-type]
    summary="List orders",
    description="List orders with filters and pagination (Fluent Specification)",
)
async def list_orders(
    service: Annotated[OrderQueryService, Depends(get_order_query_service)],
    customer_id: str | None = None,
    status: str | None = None,
    min_amount: float | None = None,
    max_amount: float | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """List orders using FluentSpecificationBuilder-backed query service."""
    return await service.list_orders_with_specification(
        customer_id=customer_id,
        status=status,
        min_amount=min_amount,
        max_amount=max_amount,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{order_id}",
    response_model=dict[str, Any],
    responses=get_error_responses_schema(),  # type: ignore[arg-type]
    summary="Get an order",
    description="Retrieve an order by ID",
)
async def get_order(
    order_id: str,
    use_case: Annotated[GetOrderUseCase, Depends(get_get_order_use_case)],
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
    responses=get_error_responses_schema(),  # type: ignore[arg-type]
    summary="Pay for an order",
    description="Mark an order as paid",
)
async def pay_order(
    order_id: str,
    request: PayOrderRequest,
    use_case: Annotated[PayOrderUseCase, Depends(get_pay_order_use_case)],
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
    responses=get_error_responses_schema(),  # type: ignore[arg-type]
    summary="Cancel an order",
    description="Cancel a pending order",
)
async def cancel_order(
    order_id: str,
    request: CancelOrderRequest,
    use_case: Annotated[CancelOrderUseCase, Depends(get_cancel_order_use_case)],
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
