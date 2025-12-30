"""Order API Request Models.

These models define the structure of HTTP requests for the Order API.
They are specific to the REST API layer and handle API input validation.
"""

from pydantic import BaseModel, Field


class OrderItemRequest(BaseModel):
    """Order item request model for API input."""

    product_id: str = Field(..., description="Product ID")
    product_name: str = Field(..., min_length=1, description="Product name")
    quantity: int = Field(..., gt=0, description="Quantity")
    unit_price: float = Field(..., gt=0, description="Unit price")


class CreateOrderRequest(BaseModel):
    """Create order request model.

    Note: For idempotency, pass X-Idempotency-Key in HTTP Header.
    """

    customer_id: str = Field(..., description="Customer ID")
    items: list[OrderItemRequest] = Field(..., min_length=1, description="Order items")

    class Config:
        json_schema_extra = {
            "example": {
                "customer_id": "customer-456",
                "items": [
                    {
                        "product_id": "product-001",
                        "product_name": "Laptop",
                        "quantity": 1,
                        "unit_price": 999.99,
                    }
                ],
            }
        }


class PayOrderRequest(BaseModel):
    """Pay order request model.

    Note: For idempotency, pass X-Idempotency-Key in HTTP Header.
    """

    pass  # Empty body, idempotency handled via Header


class ShipOrderRequest(BaseModel):
    """Ship order request model.

    Note: For idempotency, pass X-Idempotency-Key in HTTP Header.
    """

    tracking_number: str | None = Field(None, description="Shipment tracking number")

    class Config:
        json_schema_extra = {
            "example": {
                "tracking_number": "SF123456789",
            }
        }


class CancelOrderRequest(BaseModel):
    """Cancel order request model."""

    reason: str = Field(..., min_length=1, description="Cancellation reason")

    class Config:
        json_schema_extra = {
            "example": {
                "reason": "Customer requested cancellation",
            }
        }
