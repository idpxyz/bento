"""Persistence layer for data storage.

This is the Infrastructure layer in DDD/Hexagonal Architecture.
Contains technical implementations for data persistence.

Structure:
- po/: Persistence Object (PO) base classes and mixins
- repository/: Repository implementations (BaseRepository, InMemoryRepository)
- interceptor/: Cross-cutting concerns (audit, soft-delete, optimistic locking)
- specification/: Query specification pattern
- uow.py: Unit of Work pattern

Provides:
- Base: SQLAlchemy declarative base for all ORM models
- Mixins: Reusable field mixins for audit, soft-delete, and optimistic locking
"""

from bento.persistence.po import (
    AuditFieldsMixin,
    Base,
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
