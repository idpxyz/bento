"""Cache Invalidation Configuration for cross-entity relationships.

Automatically invalidate related entity caches when domain events occur.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CacheInvalidationRule:
    """Rule for invalidating cache when an event occurs.

    Attributes:
        event_type: The domain event class that triggers invalidation
        target_entity: The entity type whose cache should be invalidated
        pattern_generator: Function to generate cache key patterns to delete
        condition: Optional condition function to check if rule applies
    """

    event_type: type
    target_entity: str
    pattern_generator: Callable[[Any], list[str]]
    condition: Callable[[Any], bool] | None = None

    def should_invalidate(self, event: Any) -> bool:
        """Check if this rule should be applied to the event."""
        if not isinstance(event, self.event_type):
            return False

        if self.condition is not None:
            return self.condition(event)

        return True

    def get_patterns(self, event: Any) -> list[str]:
        """Get cache key patterns to invalidate for this event."""
        return self.pattern_generator(event)


@dataclass
class CacheInvalidationConfig:
    """Configuration for automatic cache invalidation on domain events.

    Example:
        ```python
        config = CacheInvalidationConfig()

        # Order created -> invalidate Customer cache
        config.add_rule(
            event_type=OrderCreatedEvent,
            target_entity="Customer",
            pattern_generator=lambda e: [
                f"Customer:{e.customer_id}:orders:*",
                f"Customer:{e.customer_id}:spending:*",
            ]
        )

        # Product price changed -> invalidate Product rankings
        config.add_rule(
            event_type=ProductPriceChangedEvent,
            target_entity="ProductRanking",
            pattern_generator=lambda e: ["ProductRanking:*"]
        )
        ```
    """

    rules: list[CacheInvalidationRule] = field(default_factory=list)

    def add_rule(
        self,
        event_type: type,
        target_entity: str,
        pattern_generator: Callable[[Any], list[str]],
        condition: Callable[[Any], bool] | None = None,
    ) -> None:
        """Add a cache invalidation rule.

        Args:
            event_type: Domain event class that triggers invalidation
            target_entity: Entity type whose cache to invalidate
            pattern_generator: Function to generate cache key patterns
            condition: Optional condition to check if rule applies
        """
        rule = CacheInvalidationRule(
            event_type=event_type,
            target_entity=target_entity,
            pattern_generator=pattern_generator,
            condition=condition,
        )
        self.rules.append(rule)

    def get_applicable_rules(self, event: Any) -> list[CacheInvalidationRule]:
        """Get all rules that apply to the given event."""
        return [rule for rule in self.rules if rule.should_invalidate(event)]

    def get_invalidation_patterns(self, event: Any) -> list[str]:
        """Get all cache key patterns to invalidate for the event."""
        patterns = []
        for rule in self.get_applicable_rules(event):
            patterns.extend(rule.get_patterns(event))
        return patterns


# Global configuration instance
_global_config: CacheInvalidationConfig | None = None


def get_cache_invalidation_config() -> CacheInvalidationConfig:
    """Get the global cache invalidation configuration."""
    global _global_config
    if _global_config is None:
        _global_config = CacheInvalidationConfig()
    return _global_config


def configure_cache_invalidation(config: CacheInvalidationConfig) -> None:
    """Set the global cache invalidation configuration."""
    global _global_config
    _global_config = config
