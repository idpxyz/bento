"""Infrastructure adapters for Ordering context."""

# Product Catalog Adapters
# Real Adapters (真实实现)
from contexts.ordering.infrastructure.adapters.services.email_adapter import (
    EmailAdapter,
    EmailConfig,
)
from contexts.ordering.infrastructure.adapters.services.local_inventory_adapter import (
    LocalInventoryAdapter,
)

# Redis Adapter (optional, requires redis)
try:
    from contexts.ordering.infrastructure.adapters.services.redis_inventory_adapter import (
        RedisInventoryAdapter,
    )
except ImportError:
    RedisInventoryAdapter = None  # type: ignore

# Mock Adapters (用于测试和开发)
from contexts.ordering.infrastructure.adapters.services.mock_inventory_adapter import (
    MockInventoryAdapter,
)
from contexts.ordering.infrastructure.adapters.services.mock_notification_adapter import (
    MockNotificationAdapter,
)
from contexts.ordering.infrastructure.adapters.services.mock_payment_adapter import (
    MockPaymentAdapter,
)
from contexts.ordering.infrastructure.adapters.services.product_catalog_adapter import (
    ProductCatalogAdapter,
)

__all__ = [
    # Real Adapters
    "ProductCatalogAdapter",
    "EmailAdapter",
    "EmailConfig",
    "LocalInventoryAdapter",
    "RedisInventoryAdapter",
    # Mock Adapters
    "MockPaymentAdapter",
    "MockNotificationAdapter",
    "MockInventoryAdapter",
    # Factory (for convenience)
    "AdapterFactory",
    "create_adapters",
]

# Import factory for convenience
try:
    from contexts.ordering.infrastructure.adapters.adapter_factory import (
        AdapterFactory,
        create_adapters,
    )
except ImportError:
    pass  # Factory may not be available in all contexts
