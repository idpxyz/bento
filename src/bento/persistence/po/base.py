"""SQLAlchemy declarative base for Bento framework.

Provides the root Base class for all ORM models.
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import DeclarativeBase, declared_attr


class Base(DeclarativeBase):
    """Root declarative base for all SQLAlchemy models.

    Provides shared metadata and utility methods for all models.

    Features:
    - Auto-generates __tablename__ from class name (lowercased)
    - _generate_id(): Helper method to generate UUID string IDs
    - Can be extended by applications for custom behavior

    Example:
        ```python
        from bento.persistence import Base

        class UserModel(Base):
            # __tablename__ auto-generated as "usermodel"
            id: Mapped[str] = mapped_column(String, primary_key=True)

        # Or explicitly specify:
        class OrderModel(Base):
            __tablename__ = "orders"  # Override auto-generation
            # ... fields
        ```
    """

    @declared_attr.directive
    def __tablename__(cls) -> str:

        """Auto-generate table name from class name (lowercased).

        Can be overridden by explicitly setting __tablename__ in subclass.
        """
        return cls.__name__.lower()

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
