"""Data Transfer Objects for Order module."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class OrderItemDTO:
    """Order item data transfer object."""
    
    product_id: str
    product_name: str
    quantity: int
    unit_price: float
    subtotal: float  # quantity * unit_price


@dataclass
class OrderDTO:
    """Order data transfer object."""
    
    order_id: str
    customer_id: str
    status: str
    items: list[OrderItemDTO]
    total_amount: float
    created_at: datetime
    updated_at: datetime | None = None
    paid_at: datetime | None = None
    cancelled_at: datetime | None = None
    cancellation_reason: str | None = None

