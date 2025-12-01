"""HybridMessageBus - Smart event publishing based on business context.

This module provides intelligent event routing based on:
- Event type and business context
- Performance requirements (latency vs reliability)
- Bounded Context boundaries (intra-BC vs inter-BC)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, runtime_checkable

from bento.domain.domain_event import DomainEvent


class PublishStrategy(Enum):
    """Event publishing strategies for different scenarios."""

    SYNC_ONLY = "sync_only"  # Fast intra-BC events
    ASYNC_ONLY = "async_only"  # Reliable inter-BC events
    HYBRID_FAST = "hybrid_fast"  # Try sync first, fallback async
    HYBRID_RELIABLE = "hybrid_reliable"  # Async first, sync confirmation


class EventScope(Enum):
    """Event scope for routing decisions."""

    INTRA_BC = "intra_bc"  # Within same Bounded Context
    INTER_BC = "inter_bc"  # Cross Bounded Context
    EXTERNAL = "external"  # External system integration


@dataclass
class PublishConfig:
    """Configuration for event publishing behavior."""

    strategy: PublishStrategy = PublishStrategy.HYBRID_FAST
    scope: EventScope = EventScope.INTRA_BC
    timeout_ms: int = 100
    retry_attempts: int = 3
    circuit_breaker: bool = True

    # Business context metadata
    bounded_context: str = "default"
    priority: int = 5  # 1-10, higher = more important
    tags: list[str] = field(default_factory=list)


@runtime_checkable
class HybridMessageBus(Protocol):
    """Hybrid Message Bus for intelligent event publishing.

    Provides smart routing based on event characteristics:
    - Intra-BC events: Fast synchronous publishing
    - Inter-BC events: Reliable asynchronous publishing
    - Critical events: Hybrid with fallback guarantees

    Example:
        ```python
        # Configure per event type
        bus.configure_event(OrderCreatedEvent, PublishConfig(
            strategy=PublishStrategy.HYBRID_RELIABLE,
            scope=EventScope.INTER_BC,
            bounded_context="orders"
        ))

        # Smart publishing
        await bus.publish(order_created_event)  # Auto-routes based on config
        ```
    """

    async def publish(
        self, events: DomainEvent | list[DomainEvent], config: PublishConfig | None = None
    ) -> None:
        """Publish events with intelligent routing.

        Args:
            events: Event(s) to publish
            config: Optional override configuration
        """
        ...

    def configure_event(self, event_type: type[DomainEvent], config: PublishConfig) -> None:
        """Configure publishing strategy for specific event type.

        Args:
            event_type: The event class
            config: Publishing configuration
        """
        ...

    def configure_bounded_context(self, bc_name: str, default_config: PublishConfig) -> None:
        """Configure default publishing strategy for a Bounded Context.

        Args:
            bc_name: Bounded Context name
            default_config: Default configuration for this BC
        """
        ...

    async def get_metrics(self) -> dict:
        """Get publishing metrics and performance stats."""
        ...


# Pre-configured strategies for common scenarios
class PublishStrategies:
    """Pre-configured publishing strategies for common use cases."""

    # Fast intra-BC communication
    INTRA_BC_FAST = PublishConfig(
        strategy=PublishStrategy.SYNC_ONLY,
        scope=EventScope.INTRA_BC,
        timeout_ms=50,
        retry_attempts=1,
        circuit_breaker=False,
    )

    # Reliable inter-BC communication
    INTER_BC_RELIABLE = PublishConfig(
        strategy=PublishStrategy.ASYNC_ONLY,
        scope=EventScope.INTER_BC,
        timeout_ms=1000,
        retry_attempts=5,
        circuit_breaker=True,
    )

    # Critical business events (best of both worlds)
    CRITICAL_HYBRID = PublishConfig(
        strategy=PublishStrategy.HYBRID_RELIABLE,
        scope=EventScope.INTER_BC,
        timeout_ms=200,
        retry_attempts=3,
        circuit_breaker=True,
        priority=9,
    )

    # External system integration
    EXTERNAL_INTEGRATION = PublishConfig(
        strategy=PublishStrategy.ASYNC_ONLY,
        scope=EventScope.EXTERNAL,
        timeout_ms=5000,
        retry_attempts=5,
        circuit_breaker=True,
        priority=7,
    )
