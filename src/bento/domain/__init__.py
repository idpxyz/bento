"""Domain layer - business logic and domain models.

This module contains the core business entities, value objects, and domain services.
"""

from bento.domain.aggregate import AggregateRoot
from bento.domain.domain_event import DomainEvent
from bento.domain.entity import Entity
from bento.domain.event_registry import (
    deserialize_event,
    get_event_class,
    register_event,
)
from bento.domain.ports.repository import Repository
from bento.domain.service import DomainService
from bento.domain.specification import Specification
from bento.domain.value_object import ValueObject

__all__ = [
    "AggregateRoot",
    "DomainEvent",
    "Entity",
    "Repository",
    "DomainService",
    "Specification",
    "ValueObject",
    "register_event",
    "get_event_class",
    "deserialize_event",
]
