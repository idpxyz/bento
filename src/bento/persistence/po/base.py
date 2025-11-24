"""SQLAlchemy declarative base for Bento framework.

Provides the root Base class for all ORM models.
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Root declarative base for all SQLAlchemy models.

    Provides shared metadata and utility methods for all models.

    Features:
    - _generate_id(): Helper method to generate UUID string IDs
    - Can be extended by applications for custom behavior

    Example:
        ```python
        from bento.persistence import Base

        class UserModel(Base):
            __tablename__ = "users"
            # ... fields
        ```
    """

    @staticmethod
    def _generate_id() -> str:
        """Generate a UUID string for primary keys.

        Returns:
            UUID string suitable for database primary key

        Example:
            ```python
            class UserModel(Base):
                __tablename__ = "users"
                id: Mapped[str] = mapped_column(
                    String(36),
                    primary_key=True,
                    default=Base._generate_id
                )
            ```
        """
        return str(uuid4())
