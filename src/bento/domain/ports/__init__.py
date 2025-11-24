"""Domain layer ports (interfaces).

This module defines the ports (contracts) that the domain layer depends on.
All ports should be defined as Protocol classes to maintain dependency inversion.
"""

from bento.domain.ports.event_publisher import EventPublisher
from bento.domain.ports.repository import (  # Repository for backward compatibility
    IRepository,
)
from bento.domain.ports.specification import Specification

__all__ = [
    "EventPublisher",
    "IRepository",
    "Specification",
]
