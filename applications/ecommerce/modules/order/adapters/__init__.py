"""Order adapters layer (legacy).

DEPRECATED: Adapters have been moved to modules/order/persistence/
for better Hexagonal Architecture with modular persistence.

Import from:
- applications.ecommerce.modules.order.persistence
"""

# For backward compatibility, re-export from new locations
from applications.ecommerce.modules.order.persistence import (
    OrderItemMapper,
    OrderMapper,
    OrderRepository,
)

__all__ = [
    "OrderRepository",
    "OrderMapper",
    "OrderItemMapper",
]
