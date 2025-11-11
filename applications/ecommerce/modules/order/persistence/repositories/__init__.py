"""Order module repository implementations.

Concrete repository implementations (adapters) for Order aggregate.
"""

from applications.ecommerce.modules.order.persistence.repositories.order_repository import (
    OrderRepository,
)

__all__ = [
    "OrderRepository",
]
