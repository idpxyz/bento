"""Events"""

from contexts.catalog.domain.events.categorycreated_event import CategoryCreated
from contexts.catalog.domain.events.categorydeleted_event import CategoryDeleted

__all__ = [
    "CategoryCreated",
    "CategoryDeleted",
]
