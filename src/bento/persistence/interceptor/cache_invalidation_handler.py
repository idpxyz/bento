"""Automatic cache invalidation handler for domain events.

This handler listens to domain events and automatically invalidates
related entity caches based on configured rules.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bento.application.ports.cache import Cache
    from bento.persistence.interceptor.cache_invalidation_config import (
        CacheInvalidationConfig,
    )

logger = logging.getLogger(__name__)


class AutoCacheInvalidationHandler:
    """Automatic cache invalidation handler for domain events.

    This handler automatically invalidates related entity caches when
    domain events occur, based on configured invalidation rules.

    Example:
        ```python
        # 1. Configure invalidation rules
        config = CacheInvalidationConfig()
        config.add_rule(
            event_type=OrderCreatedEvent,
            target_entity="Customer",
            pattern_generator=lambda e: [f"Customer:{e.customer_id}:*"]
        )

        # 2. Create handler
        handler = AutoCacheInvalidationHandler(cache, config)

        # 3. Register as event handler
        event_bus.subscribe(handler.handle_event)

        # 4. Events are automatically handled
        await event_bus.publish(OrderCreatedEvent(...))
        # → Customer cache automatically invalidated
        ```
    """

    def __init__(
        self,
        cache: Cache,
        config: CacheInvalidationConfig,
        prefix: str = "",
    ) -> None:
        """Initialize the handler.

        Args:
            cache: Cache instance to invalidate
            config: Cache invalidation configuration
            prefix: Optional prefix for cache keys
        """
        self._cache = cache
        self._config = config
        self._prefix = prefix

    async def handle_event(self, event: Any) -> None:
        """Handle a domain event and invalidate related caches.

        Args:
            event: Domain event to handle
        """
        # Get invalidation patterns for this event
        patterns = self._config.get_invalidation_patterns(event)

        if not patterns:
            # No rules apply to this event
            return

        # Invalidate caches
        event_name = event.__class__.__name__
        logger.info(f"Auto-invalidating cache for event {event_name}: {len(patterns)} patterns")

        for pattern in patterns:
            full_pattern = f"{self._prefix}{pattern}" if self._prefix else pattern

            try:
                await self._cache.delete_pattern(full_pattern)
                logger.debug(f"Invalidated cache pattern: {full_pattern}")
            except Exception as e:
                logger.error(
                    f"Failed to invalidate cache pattern {full_pattern}: {e}",
                    exc_info=True,
                )

    def add_rule(
        self,
        event_type: type,
        target_entity: str,
        pattern_generator: Any,
        condition: Any = None,
    ) -> None:
        """Add a cache invalidation rule.

        Convenience method to add rules without directly accessing config.

        Args:
            event_type: Domain event class that triggers invalidation
            target_entity: Entity type whose cache to invalidate
            pattern_generator: Function to generate cache key patterns
            condition: Optional condition to check if rule applies
        """
        self._config.add_rule(
            event_type=event_type,
            target_entity=target_entity,
            pattern_generator=pattern_generator,
            condition=condition,
        )
