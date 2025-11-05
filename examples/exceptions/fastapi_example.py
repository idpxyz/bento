"""FastAPI integration example.

This example demonstrates how to use the exception system with FastAPI.

Run:
    uvicorn examples.exceptions.fastapi_example:app --reload

Then visit:
    http://localhost:8000/docs
"""

import logging
from typing import Any

from fastapi import FastAPI, Query
from pydantic import BaseModel

from core.error_codes import CommonErrors
from examples.error_codes.order_errors import OrderErrors
from core.error_handler import (
    get_error_responses_schema,
    register_exception_handlers,
)
from core.errors import ApplicationException, DomainException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Bento Exception Example API",
    description="Demonstrates exception handling in FastAPI",
    version="1.0.0",
)

# Register exception handlers
register_exception_handlers(app)


# ==================== Models ====================


class CreateOrderRequest(BaseModel):
    """Create order request."""

    customer_id: str
    items: list[dict[str, Any]]


class OrderResponse(BaseModel):
    """Order response."""

    order_id: str
    customer_id: str
    status: str
    items: list[dict[str, Any]]


# ==================== In-memory storage ====================

orders_db: dict[str, dict[str, Any]] = {}


# ==================== Routes ====================


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "message": "Bento Exception Example API",
        "docs": "/docs",
    }


@app.post(
    "/orders",
    response_model=OrderResponse,
    responses=get_error_responses_schema(),
    summary="Create an order",
    description="Create a new order with validation",
)
async def create_order(request: CreateOrderRequest) -> OrderResponse:
    """Create a new order.

    This endpoint demonstrates:
    - Parameter validation (ApplicationException)
    - Business rule validation (DomainException)
    - Automatic error response formatting
    """
    # Application-level validation
    if not request.customer_id:
        raise ApplicationException(
            error_code=CommonErrors.INVALID_PARAMS,
            details={"field": "customer_id", "reason": "cannot be empty"},
        )

    if not request.items or len(request.items) == 0:
        raise ApplicationException(
            error_code=CommonErrors.INVALID_PARAMS,
            details={"field": "items", "reason": "must contain at least one item"},
        )

    # Generate order ID
    order_id = f"ORDER-{len(orders_db) + 1:04d}"

    # Domain-level validation: check if duplicate
    if order_id in orders_db:
        raise DomainException(
            error_code=CommonErrors.RESOURCE_CONFLICT,
            details={"order_id": order_id},
        )

    # Create order
    order = {
        "order_id": order_id,
        "customer_id": request.customer_id,
        "status": "pending",
        "items": request.items,
    }

    orders_db[order_id] = order

    logger.info(f"Order created: {order_id}")

    return OrderResponse(**order)


@app.get(
    "/orders/{order_id}",
    response_model=OrderResponse,
    responses=get_error_responses_schema(),
    summary="Get an order",
    description="Retrieve an order by ID",
)
async def get_order(order_id: str) -> OrderResponse:
    """Get order by ID.

    This endpoint demonstrates:
    - Not found error handling
    - Automatic error response formatting
    """
    if order_id not in orders_db:
        raise DomainException(
            error_code=OrderErrors.ORDER_NOT_FOUND,
            details={"order_id": order_id},
        )

    order = orders_db[order_id]
    return OrderResponse(**order)


@app.put(
    "/orders/{order_id}/pay",
    response_model=OrderResponse,
    responses=get_error_responses_schema(),
    summary="Pay for an order",
    description="Mark an order as paid",
)
async def pay_order(order_id: str) -> OrderResponse:
    """Pay for an order.

    This endpoint demonstrates:
    - State transition validation
    - Business rule enforcement
    """
    if order_id not in orders_db:
        raise DomainException(
            error_code=OrderErrors.ORDER_NOT_FOUND,
            details={"order_id": order_id},
        )

    order = orders_db[order_id]

    # Business rule: cannot pay twice
    if order["status"] == "paid":
        raise DomainException(
            error_code=OrderErrors.ORDER_ALREADY_PAID,
            details={"order_id": order_id, "current_status": order["status"]},
        )

    # Business rule: cannot pay cancelled order
    if order["status"] == "cancelled":
        raise DomainException(
            error_code=OrderErrors.ORDER_ALREADY_CANCELLED,
            details={"order_id": order_id},
        )

    # Update status
    order["status"] = "paid"
    logger.info(f"Order {order_id} paid")

    return OrderResponse(**order)


@app.delete(
    "/orders/{order_id}",
    responses=get_error_responses_schema(),
    summary="Cancel an order",
    description="Cancel a pending order",
)
async def cancel_order(order_id: str) -> dict[str, str]:
    """Cancel an order.

    This endpoint demonstrates:
    - Deletion validation
    - Business rule enforcement
    """
    if order_id not in orders_db:
        raise DomainException(
            error_code=OrderErrors.ORDER_NOT_FOUND,
            details={"order_id": order_id},
        )

    order = orders_db[order_id]

    # Business rule: cannot cancel paid order
    if order["status"] == "paid":
        raise DomainException(
            error_code=OrderErrors.ORDER_ALREADY_PAID,
            details={
                "order_id": order_id,
                "reason": "Cannot cancel paid order",
            },
        )

    # Update status
    order["status"] = "cancelled"
    logger.info(f"Order {order_id} cancelled")

    return {"message": f"Order {order_id} cancelled"}


@app.get(
    "/orders",
    response_model=list[OrderResponse],
    summary="List all orders",
    description="Get all orders (optionally filtered by status)",
)
async def list_orders(
    status: str | None = Query(None, description="Filter by status")
) -> list[OrderResponse]:
    """List all orders, optionally filtered by status."""
    orders = list(orders_db.values())

    if status:
        orders = [o for o in orders if o["status"] == status]

    return [OrderResponse(**order) for order in orders]


@app.get(
    "/demo/trigger-error",
    responses=get_error_responses_schema(),
    summary="Trigger test error",
    description="Trigger an error for testing exception handling",
)
async def trigger_error(
    error_type: str = Query(
        "not_found",
        description="Error type: not_found, invalid_params, conflict, unauthorized",
    )
) -> dict[str, str]:
    """Trigger different types of errors for testing."""
    if error_type == "not_found":
        raise DomainException(
            error_code=OrderErrors.ORDER_NOT_FOUND,
            details={"order_id": "TEST-001"},
        )
    elif error_type == "invalid_params":
        raise ApplicationException(
            error_code=CommonErrors.INVALID_PARAMS,
            details={"field": "test", "reason": "invalid value"},
        )
    elif error_type == "conflict":
        raise DomainException(
            error_code=CommonErrors.RESOURCE_CONFLICT,
            details={"resource": "test"},
        )
    elif error_type == "unauthorized":
        raise ApplicationException(
            error_code=CommonErrors.UNAUTHORIZED,
            details={"reason": "test unauthorized"},
        )
    else:
        return {"message": f"Unknown error type: {error_type}"}


# ==================== Startup ====================


@app.on_event("startup")
async def startup_event() -> None:
    """Application startup."""
    logger.info("🚀 FastAPI application started")
    logger.info("📖 API docs: http://localhost:8000/docs")
    logger.info("🔬 Try these endpoints:")
    logger.info("   POST   /orders              - Create order")
    logger.info("   GET    /orders/{id}         - Get order")
    logger.info("   PUT    /orders/{id}/pay     - Pay order")
    logger.info("   DELETE /orders/{id}         - Cancel order")
    logger.info("   GET    /demo/trigger-error  - Test errors")


if __name__ == "__main__":
    """Run with uvicorn."""
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

