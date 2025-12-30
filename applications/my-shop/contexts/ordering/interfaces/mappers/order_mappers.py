"""Order mappers for Domain → DTO → Response conversion.

This module provides conversion functions for the complete transformation chain:
1. Domain objects (Order, OrderItem) → Application DTOs (using AutoMapper)
2. Application DTOs → Interface Response models (using PydanticResponseMapper)

Performance: Uses Bento's AutoMapper for Domain→DTO, and PydanticResponseMapper for DTO→Response.
"""

from bento.application.dto import AutoMapper, PydanticResponseMapper

from contexts.ordering.application.dto.order_dto import OrderDTO, OrderItemDTO
from contexts.ordering.domain.models.order import Order, OrderItem
from contexts.ordering.interfaces.dto.order_responses import OrderItemResponse, OrderResponse


# ==================== Domain → DTO (using AutoMapper) ====================


class OrderItemDTOMapper(AutoMapper[OrderItem, OrderItemDTO]):
    """OrderItem Domain → DTO Mapper - Zero Configuration! 🤖"""

    def __init__(self):
        super().__init__(OrderItem, OrderItemDTO)


class OrderDTOMapper(AutoMapper[Order, OrderDTO]):
    """Order Domain → DTO Mapper - Smart Automation! 🤖"""

    def __init__(self):
        super().__init__(Order, OrderDTO)
        self.item_mapper = OrderItemDTOMapper()

        self.field_mappings = {
            "items": lambda order: self.item_mapper.to_dto_list(order.items),
        }


# ==================== DTO → Response (using PydanticResponseMapper) ====================


class OrderItemResponseMapper(PydanticResponseMapper[OrderItemDTO, OrderItemResponse]):
    """OrderItem DTO → Response Mapper - Zero Configuration! 🤖

    Uses Bento's PydanticResponseMapper for automatic conversion.
    """

    def __init__(self):
        super().__init__(OrderItemDTO, OrderItemResponse)


class OrderResponseMapper(PydanticResponseMapper[OrderDTO, OrderResponse]):
    """Order DTO → Response Mapper - Smart Automation! 🤖

    Uses Bento's PydanticResponseMapper for automatic conversion.
    """

    def __init__(self):
        super().__init__(OrderDTO, OrderResponse)


# ==================== Singleton Instances ====================


_order_item_dto_mapper = OrderItemDTOMapper()
_order_dto_mapper = OrderDTOMapper()
_order_item_response_mapper = OrderItemResponseMapper()
_order_response_mapper = OrderResponseMapper()


# ==================== Convenience Functions ====================


def order_domain_to_dto(order: Order) -> OrderDTO:
    """Convert Order domain object to OrderDTO using AutoMapper."""
    return _order_dto_mapper.to_dto(order)


def order_dto_to_response(dto: OrderDTO) -> OrderResponse:
    """Convert OrderDTO to OrderResponse using PydanticResponseMapper."""
    return _order_response_mapper.to_response(dto)


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
