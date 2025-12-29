"""CategoryCreated domain event"""

from dataclasses import dataclass

from bento.domain.domain_event import DomainEvent
from bento.domain.event_registry import register_event


@register_event
@dataclass(frozen=True, kw_only=True)
class CategoryCreated(DomainEvent):
    """CategoryCreated event

    Triggered when a new category is created.

    The framework automatically handles:
    - Event persistence (Outbox)
    - Event publishing (Message Queue)
    - Event tracking (event_id, occurred_at)
    """

    topic: str = "category.created"

    # Event fields
    category_id: str
    category_name: str
    parent_id: str | None = None
