"""Order DTO - Data Transfer Object for Order queries."""

from datetime import datetime

from bento.application.dto import BaseDTO
from pydantic import Field


class OrderItemDTO(BaseDTO):
    """Order Item Data Transfer Object."""

    id: str = Field(..., description="Order item ID")
    product_id: str = Field(..., description="Product ID")
    product_name: str = Field(..., min_length=1, description="Product name")
    quantity: int = Field(..., gt=0, description="Quantity")
    unit_price: float = Field(..., gt=0, description="Unit price")
    subtotal: float = Field(..., ge=0, description="Subtotal")


class OrderDTO(BaseDTO):
    """Order Data Transfer Object."""

    id: str = Field(..., description="Order ID")
    customer_id: str = Field(..., description="Customer ID")
    status: str = Field(..., description="Order status")
    items: list[OrderItemDTO] = Field(..., description="Order items")
    total: float = Field(..., ge=0, description="Order total")
    created_at: datetime | None = Field(None, description="Created timestamp")
    paid_at: datetime | None = Field(None, description="Paid timestamp")
    shipped_at: datetime | None = Field(None, description="Shipped timestamp")
