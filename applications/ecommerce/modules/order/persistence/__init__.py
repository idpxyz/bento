"""Order module persistence layer.

Contains all infrastructure code for Order aggregate:
- Models: SQLAlchemy ORM definitions
- Mappers: Domain ↔ Persistence conversion
- Repositories: Data access implementations (adapters)

Following Hexagonal Architecture with modular persistence per aggregate.
"""

from applications.ecommerce.modules.order.persistence.mappers import (
    OrderItemMapper,
    OrderMapper,
)
from applications.ecommerce.modules.order.persistence.models import (
    OrderItemModel,
    OrderModel,
)
from applications.ecommerce.modules.order.persistence.repositories import (
    OrderRepository,
)

__all__ = [
    # Models
    "OrderModel",
    "OrderItemModel",
    # Mappers
    "OrderMapper",
    "OrderItemMapper",
    # Repositories
    "OrderRepository",
]
