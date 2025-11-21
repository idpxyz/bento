"""Domain ports (interfaces) for Ordering context.

Ports define the contracts that adapters must implement.
Following Hexagonal Architecture principles.
"""

# Repository Ports
from contexts.ordering.domain.ports.repositories.i_order_repository import (
    IOrderRepository,
)

# Service Ports
from contexts.ordering.domain.ports.services.i_inventory_service import (
    IInventoryService,
)
from contexts.ordering.domain.ports.services.i_notification_service import (
    INotificationService,
)
from contexts.ordering.domain.ports.services.i_payment_service import (
    IPaymentService,
)
from contexts.ordering.domain.ports.services.i_product_catalog_service import (
    IProductCatalogService,
)

__all__ = [
    # Repository Ports
    "IOrderRepository",
    # Service Ports
    "IProductCatalogService",
    "IPaymentService",
    "INotificationService",
    "IInventoryService",
]
