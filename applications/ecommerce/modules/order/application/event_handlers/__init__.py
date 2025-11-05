"""Order event handlers.

Event handlers process domain events and trigger side effects.
They demonstrate the event-driven architecture pattern.
"""

from applications.ecommerce.modules.order.application.event_handlers.event_listener import (
    OrderEventListener,
    create_event_listener,
)
from applications.ecommerce.modules.order.application.event_handlers.order_event_handler import (
    OrderEventHandler,
)

__all__ = ["OrderEventHandler", "OrderEventListener", "create_event_listener"]
