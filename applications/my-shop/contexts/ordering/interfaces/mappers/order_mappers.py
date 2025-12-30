"""Order mappers for Domain → DTO → Response conversion.

This module provides conversion functions for the complete transformation chain:
1. Domain objects (Order, OrderItem) → Application DTOs
2. Application DTOs → Interface Response models
"""

from contexts.ordering.application.dto.order_dto import OrderDTO, OrderItemDTO
from contexts.ordering.domain.models.order import Order, OrderItem
from contexts.ordering.interfaces.dto.order_responses import (
    OrderItemResponse,
    OrderResponse,
)


# ==================== Domain → DTO ====================


def order_item_domain_to_dto(item: OrderItem) -> OrderItemDTO:
    """Convert OrderItem domain object to OrderItemDTO.

    Args:
        item: Domain OrderItem

    Returns:
        Application layer OrderItemDTO
    """
    return OrderItemDTO(
        id=str(item.id),
        product_id=str(item.product_id),
        product_name=item.product_name,
        quantity=item.quantity,
        unit_price=float(item.unit_price),
        subtotal=float(item.subtotal),
    )


def order_domain_to_dto(order: Order) -> OrderDTO:
    """Convert Order domain object to OrderDTO.

    Args:
        order: Domain Order aggregate

    Returns:
        Application layer OrderDTO
    """
    return OrderDTO(
        id=str(order.id),
        customer_id=str(order.customer_id),
        status=order.status.value if hasattr(order.status, "value") else order.status,
        items=[order_item_domain_to_dto(item) for item in order.items],
        total=float(order.total),
        created_at=order.created_at,
        paid_at=order.paid_at,
        shipped_at=order.shipped_at,
    )


# ==================== DTO → Response ====================


def order_item_dto_to_response(dto: OrderItemDTO) -> OrderItemResponse:
    """Convert OrderItemDTO to OrderItemResponse.

    Args:
        dto: Application layer OrderItemDTO

    Returns:
        Interface layer OrderItemResponse
    """
    return OrderItemResponse(
        id=dto.id,
        product_id=dto.product_id,
        product_name=dto.product_name,
        quantity=dto.quantity,
        unit_price=dto.unit_price,
        subtotal=dto.subtotal,
    )


def order_dto_to_response(dto: OrderDTO) -> OrderResponse:
    """Convert OrderDTO to OrderResponse.

    Args:
        dto: Application layer OrderDTO

    Returns:
        Interface layer OrderResponse
    """
    return OrderResponse(
        id=dto.id,
        customer_id=dto.customer_id,
        status=dto.status,
        items=[order_item_dto_to_response(item) for item in dto.items],
        total=dto.total,
        created_at=dto.created_at,
        paid_at=dto.paid_at,
        shipped_at=dto.shipped_at,
    )


# ==================== Convenience Functions ====================


def order_to_response(order: Order | OrderDTO) -> OrderResponse:
    """Convert Order (domain or DTO) to OrderResponse.

    This is a convenience function that handles both domain objects
    and DTOs, automatically converting as needed.

    Args:
        order: Either a domain Order or OrderDTO

    Returns:
        Interface layer OrderResponse
    """
    if isinstance(order, Order):
        # Domain → DTO → Response
        dto = order_domain_to_dto(order)
        return order_dto_to_response(dto)
    else:
        # DTO → Response
        return order_dto_to_response(order)
