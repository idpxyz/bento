"""Service ports for Ordering context.

Service ports define the contracts for external services.
Following Hexagonal Architecture principles.
"""

from contexts.ordering.domain.ports.services.i_inventory_service import (
    IInventoryService,
    InventoryItem,
    ReservationRequest,
    ReservationResult,
)
from contexts.ordering.domain.ports.services.i_notification_service import (
    INotificationService,
    NotificationPriority,
    NotificationRequest,
    NotificationResult,
    NotificationType,
)
from contexts.ordering.domain.ports.services.i_payment_service import (
    IPaymentService,
    PaymentMethod,
    PaymentRequest,
    PaymentResult,
    PaymentStatus,
)
from contexts.ordering.domain.ports.services.i_product_catalog_service import (
    IProductCatalogService,
)

__all__ = [
    # Services
    "IProductCatalogService",
    "IPaymentService",
    "INotificationService",
    "IInventoryService",
    # Payment types
    "PaymentMethod",
    "PaymentStatus",
    "PaymentRequest",
    "PaymentResult",
    # Notification types
    "NotificationType",
    "NotificationPriority",
    "NotificationRequest",
    "NotificationResult",
    # Inventory types
    "InventoryItem",
    "ReservationRequest",
    "ReservationResult",
]
