"""Persistence layer for data storage.

Provides:
- Base: SQLAlchemy declarative base for all ORM models
- Mixins: Reusable field mixins for audit, soft-delete, and optimistic locking
"""

from bento.persistence.base import Base
from bento.persistence.mixins import (
    AuditFieldsMixin,
    FullAuditMixin,
    OptimisticLockFieldMixin,
    SoftDeleteFieldsMixin,
)

__all__ = [
    # Base class
    "Base",
    # Mixins
    "AuditFieldsMixin",
    "SoftDeleteFieldsMixin",
    "OptimisticLockFieldMixin",
    "FullAuditMixin",
]
