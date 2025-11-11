"""Domain ports (interfaces) for Order module.

Ports define the contracts that adapters must implement.
Following Hexagonal Architecture principles.
"""

from applications.ecommerce.modules.order.domain.ports.order_repository import (
    IOrderRepository,
)

__all__ = [
    "IOrderRepository",
]

