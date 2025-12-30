"""Uniqueness Checks Mixin for BaseRepository.

Provides field uniqueness validation:
- is_field_unique_po: Check if field value is unique
- find_po_by_field: Find entity by field value
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import select

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class UniquenessChecksMixin:
    """Mixin providing uniqueness checks for repositories.

    This mixin assumes the class has:
    - self._po_type: The persistence object type
    - self._session: AsyncSession instance
    """

    # Type hints for attributes provided by BaseRepository
    _po_type: type[Any]
    _session: AsyncSession

    async def is_field_unique_po(
        self, field: str, value: Any, exclude_id: Any | None = None
    ) -> bool:
        """Check if a field value is unique across all entities.

        Args:
            field: Field name to check
            value: Value to check for uniqueness
            exclude_id: Optional ID to exclude from check (useful for updates)

        Returns:
            True if value is unique, False otherwise

        Example:
            ```python
            # Creating new user
            if not await repo.is_field_unique_po("email", "user@example.com"):
                raise ValidationError("Email already exists")

            # Updating existing user (exclude current user's ID)
            if not await repo.is_field_unique_po(
                "email", new_email, exclude_id=user.id
            ):
                raise ValidationError("Email already taken")
            ```
        """
        stmt = select(self._po_type).where(

            getattr(self._po_type, field) == value

        )

        if exclude_id:
            id_value = str(exclude_id.value) if hasattr(exclude_id, "value") else str(exclude_id)
            stmt = stmt.where(self._po_type.id != id_value)


        stmt = stmt.limit(1)
        result = await self._session.execute(stmt)

        return result.scalar_one_or_none() is None

    async def find_po_by_field(self, field: str, value: Any) -> Any | None:
        """Find a single persistence object by field value.

        Args:
            field: Field name to search
            value: Value to match

        Returns:
            First matching persistence object, or None if not found

        Example:
            ```python
            # Find user by email
            user_po = await repo.find_po_by_field("email", "admin@example.com")

            # Find product by SKU
            product_po = await repo.find_po_by_field("sku", "PROD-001")
            ```
        """
        stmt = (
            select(self._po_type)
            .where(

                getattr(self._po_type, field) == value

            )
            .limit(1)
        )
        result = await self._session.execute(stmt)

        return result.scalar_one_or_none()

    async def find_all_po_by_field(self, field: str, value: Any) -> list[Any]:
        """Find all persistence objects by field value.

        Args:
            field: Field name to search
            value: Value to match

        Returns:
            List of matching persistence objects (may be empty)

        Example:
            ```python
            # Find all orders by customer
            orders_po = await repo.find_all_po_by_field("customer_id", "cust-123")

            # Find all products in category
            products_po = await repo.find_all_po_by_field("category_id", "cat-456")
            ```
        """
        stmt = select(self._po_type).where(

            getattr(self._po_type, field) == value

        )
        result = await self._session.execute(stmt)

        return list(result.scalars().all())
