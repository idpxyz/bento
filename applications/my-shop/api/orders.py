"""Order API Endpoints"""

from bento.core.ids import ID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db_session
from api.schemas.order import OrderActionResponse, OrderCreate, OrderList, OrderResponse
from contexts.ordering.domain.order import Order
from contexts.ordering.domain.orderitem import OrderItem
from contexts.ordering.infrastructure.repositories.order_repository import OrderRepository

router = APIRouter()


@router.get("/", response_model=OrderList)
async def list_orders(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    session: AsyncSession = Depends(get_db_session),
):
    """
    List all orders with pagination.
    """
    repo = OrderRepository(session)

    # Get orders
    orders = await repo.list()

    # Apply pagination
    offset = (page - 1) * page_size
    total = len(orders)
    paginated_orders = orders[offset : offset + page_size]

    return OrderList(
        items=[OrderResponse.model_validate(o) for o in paginated_orders],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/", response_model=OrderResponse, status_code=201)
async def create_order(
    data: OrderCreate,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Create a new order.

    This demonstrates the DDD approach:
    1. Create domain objects
    2. Apply business rules
    3. Persist through repository
    """
    repo = OrderRepository(session)

    # Create order items (value objects)
    items = [
        OrderItem(
            id=str(ID.generate()),
            product_id=item.product_id,
            quantity=item.quantity,
            unit_price=item.unit_price,
        )
        for item in data.items
    ]

    # Create order (aggregate root)
    order = Order(
        id=str(ID.generate()),
        customer_id=data.customer_id,
        items=items,
        status="pending",
    )

    # Calculate total (business logic in domain)
    # order.calculate_total()  # If you have this method

    # Save
    await repo.save(order)
    await session.commit()

    return OrderResponse.model_validate(order)


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Get order by ID"""
    repo = OrderRepository(session)
    order = await repo.find_by_id(order_id)

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return OrderResponse.model_validate(order)


@router.post("/{order_id}/pay", response_model=OrderActionResponse)
async def pay_order(
    order_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Pay for an order.

    This would trigger domain events:
    - OrderPaidEvent
    """
    repo = OrderRepository(session)
    order = await repo.find_by_id(order_id)

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Business logic: transition state
    # order.pay()  # This should raise domain event
    order.status = "paid"

    await repo.save(order)
    await session.commit()

    return OrderActionResponse(
        order_id=order.id,
        status=order.status,
        message="Order paid successfully",
    )


@router.post("/{order_id}/ship", response_model=OrderActionResponse)
async def ship_order(
    order_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Ship an order.

    This would trigger: OrderShippedEvent
    """
    repo = OrderRepository(session)
    order = await repo.find_by_id(order_id)

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != "paid":
        raise HTTPException(status_code=400, detail="Order must be paid before shipping")

    order.status = "shipped"

    await repo.save(order)
    await session.commit()

    return OrderActionResponse(
        order_id=order.id,
        status=order.status,
        message="Order shipped successfully",
    )


@router.post("/{order_id}/cancel", response_model=OrderActionResponse)
async def cancel_order(
    order_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Cancel an order.

    This would trigger: OrderCancelledEvent
    """
    repo = OrderRepository(session)
    order = await repo.find_by_id(order_id)

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status in ["shipped", "delivered"]:
        raise HTTPException(
            status_code=400, detail="Cannot cancel order that is already shipped or delivered"
        )

    order.status = "cancelled"

    await repo.save(order)
    await session.commit()

    return OrderActionResponse(
        order_id=order.id,
        status=order.status,
        message="Order cancelled successfully",
    )
