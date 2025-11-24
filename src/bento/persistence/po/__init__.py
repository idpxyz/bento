"""Persistence Object (PO) layer - SQLAlchemy ORM models foundation.

This module provides the base classes and mixins for defining Persistence Objects.
POs are SQLAlchemy models that represent database tables.

In DDD and Hexagonal Architecture:
- POs are in the Infrastructure layer (technical implementation)
- They are separate from Domain Entities (business logic)
- Mappers convert between POs and Domain Entities

Provides:
- Base: SQLAlchemy declarative base for all ORM models
- Mixins: Reusable field mixins for common patterns (audit, soft-delete, versioning)
"""

from bento.persistence.po.base import Base
from bento.persistence.po.mixins import (
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
