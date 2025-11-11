"""CQRS projections for read model synchronization."""

from applications.ecommerce.modules.order.application.projections.order_projection import (
    OrderProjection,
)

__all__ = [
    "OrderProjection",
]

