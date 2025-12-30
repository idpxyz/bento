"""Order mappers for Domain → DTO → Response conversion.

Ultra-simplified implementation using Bento's AutoMapper and PydanticResponseMapper.
Only 20 lines of code for complete Domain → DTO → Response chain! 🎉

Architecture:
    Domain Order → (AutoMapper) → OrderDTO → (PydanticResponseMapper) → OrderResponse
"""

from functools import lru_cache

from bento.application.dto import AutoMapper, PydanticResponseMapper

from contexts.ordering.application.dto.order_dto import OrderDTO, OrderItemDTO
from contexts.ordering.domain.models.order import Order, OrderItem
from contexts.ordering.interfaces.dto.order_responses import OrderResponse


# ==================== Lazy Singleton Mappers ====================


@lru_cache(maxsize=1)
def _get_dto_mapper() -> AutoMapper[Order, OrderDTO]:
    """Get or create OrderDTOMapper singleton."""
    item_mapper = AutoMapper(OrderItem, OrderItemDTO)
    mapper = AutoMapper(Order, OrderDTO)
    mapper.field_mappings = {
        "items": lambda order: item_mapper.to_dto_list(order.items),
    }
    return mapper


@lru_cache(maxsize=1)
def _get_response_mapper() -> PydanticResponseMapper[OrderDTO, OrderResponse]:
    """Get or create OrderResponseMapper singleton."""
    return PydanticResponseMapper(OrderDTO, OrderResponse)


# ==================== Public API ====================


def order_to_response(order: Order | OrderDTO) -> OrderResponse:
    """Convert Order (domain or DTO) to OrderResponse.

    Handles both domain objects and DTOs automatically.
    Uses lazy-initialized singleton mappers for performance.

    Args:
        order: Either a domain Order or OrderDTO

    Returns:
        Interface layer OrderResponse
    """
    if isinstance(order, Order):
        # Domain → DTO → Response
        dto = _get_dto_mapper().to_dto(order)
        return _get_response_mapper().to_response(dto)
    else:
        # DTO → Response
        return _get_response_mapper().to_response(order)
