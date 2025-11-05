"""Shared SQLAlchemy persistence foundations.

* `BasePO`       minimal columns (id/created/updated).
* `SoftDeleteMixin`  logical delete flags + helper.
* `OperatorMixin`    created_by / updated_by tracking.
* `OptimisticLockMixin`  version column wired to SQLAlchemy `version_id_col`.
* `FullFeatureBasePO`  aggregate of all mixins for tables that need full
  audit + softdelete + optimisticlocking support.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import TIMESTAMP, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# ------------------ Declarative Base ------------------
class Base(DeclarativeBase):
    """Root declarative base – holds shared metadata."""

    @staticmethod
    def _generate_id() -> str:               # UUID string pk
        return str(uuid4())

    @classmethod
    def __tablename__(cls):
        return cls.__name__.lower()

# ------------------ Mix‑ins ---------------------------


class SoftDeleteMixin:
    __abstract__ = True

    deleted_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True))
    deleted_by: Mapped[str | None] = mapped_column(String(50))

    @property
    # type: ignore[override]
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def soft_delete(self, *, deleted_by: str | None = None) -> None:
        if self.is_deleted:  # idempotent
            return
        from idp.framework.shared.utils.date_time import utc_now
        self.deleted_at = utc_now()
        self.deleted_by = deleted_by


class OperatorMixin:
    __abstract__ = True

    created_by: Mapped[str | None] = mapped_column(String(50))
    updated_by: Mapped[str | None] = mapped_column(String(50))

    def set_operator(self, *, operator: str, is_create: bool = False) -> None:
        if is_create:
            self.created_by = operator
        self.updated_by = operator


class OptimisticLockMixin:
    __abstract__ = True

    version: Mapped[int] = mapped_column(Integer, default=1)
    __mapper_args__ = {"version_id_col": version}

# ------------------ Core BasePO -----------------------


class BasePO(Base):
    __abstract__ = True

    id: Mapped[str] = mapped_column(
        String(50), primary_key=True, default=Base._generate_id)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

# ------------------ Full Feature ----------------------


class FullFeatureBasePO(BasePO, SoftDeleteMixin, OperatorMixin, OptimisticLockMixin):
    """For tables requiring softdelete + auditing + optimistic locking."""
    __abstract__ = True
