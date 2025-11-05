# domain/base/entity.py
from __future__ import annotations

import abc
from typing import TYPE_CHECKING, List, Optional
import uuid

from .event import DomainEvent


class BaseEntity(abc.ABC):
    """Base class for all domain entities."""
    id: str

    def __init__(self, id: Optional[str] = None, **kwargs):
        """Initialize entity with optional id."""
        if id is not None:
            self.id = id or str(uuid.uuid4())


class BaseAggregateRoot(BaseEntity):
    """Base class for all aggregate roots."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._events: List[DomainEvent] = []

    def raise_event(self, evt: DomainEvent) -> None:
        """Raise a domain event and register it with the current UoW."""
        from idp.framework.infrastructure.persistence.sqlalchemy.uow import (
            register_event_from_aggregate,
        )
        self._events.append(evt)
        register_event_from_aggregate(evt)

    def pull_events(self) -> List[DomainEvent]:
        """Pull all pending events and clear the event list."""
        events = self._events.copy()
        self._events.clear()
        return events

    @property
    def has_unpublished_events(self):
        return bool(self._events)
