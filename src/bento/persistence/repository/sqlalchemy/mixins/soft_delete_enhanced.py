"""Soft Delete Enhanced Mixin for BaseRepository.

Provides enhanced soft delete query operations:
- find_trashed_po: Find soft-deleted entities
- find_with_trashed_po: Find including soft-deleted entities
- count_trashed_po: Count soft-deleted entities
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class SoftDeleteEnhancedMixin:
    """Mixin providing enhanced soft delete operations for repositories.

    This mixin assumes the class has:
    - self._po_type: The persistence object type with deleted_at field
    - self._session: AsyncSession instance
    """

    # Type hints for attributes provided by BaseRepository
    _po_type: type[Any]
    _session: AsyncSession

    async def find_trashed_po(self, spec: Any | None = None) -> list[Any]:
        """Find soft-deleted entities.

        Args:
            spec: Optional specification to filter entities

        Returns:
            List of soft-deleted entities

        Example:
            ```python
            # Find all trashed users
            trashed_users = await repo.find_trashed_po()

            # Find recently trashed orders
            spec = OrderSpec().deleted_after(days=7)
            recent_trashed = await repo.find_trashed_po(spec)
            ```
        """
        if not hasattr(self._po_type, "deleted_at"):
            raise AttributeError(
                f"{self._po_type.__name__} does not support soft delete "
                "(missing 'deleted_at' field)"
            )

        stmt = select(self._po_type).where(self._po_type.deleted_at.isnot(None))

        if spec:
            stmt = spec.apply(stmt, self._po_type)

        result = await self._session.execute(stmt)

        return list(result.scalars().all())

    async def find_with_trashed_po(self, spec: Any | None = None) -> list[Any]:
        """Find all entities including soft-deleted ones.

        Args:
            spec: Optional specification to filter entities

        Returns:
            List of all entities (active + soft-deleted)

        Example:
            ```python
            # Find all users including deleted
            all_users = await repo.find_with_trashed_po()

            # Find all orders for a customer including deleted
            spec = OrderSpec().customer_id_equals("cust-123")
            all_orders = await repo.find_with_trashed_po(spec)
            ```
        """
        stmt = select(self._po_type)

        if spec:
            stmt = spec.apply(stmt, self._po_type)

        result = await self._session.execute(stmt)

        return list(result.scalars().all())

    async def count_trashed_po(self, spec: Any | None = None) -> int:
        """Count soft-deleted entities.

        Args:
            spec: Optional specification to filter entities

        Returns:
            Number of soft-deleted entities

        Example:
            ```python
            # Count all trashed users
            trashed_count = await repo.count_trashed_po()

            # Count trashed orders for today
            spec = OrderSpec().deleted_today()
            today_trashed = await repo.count_trashed_po(spec)
            ```
        """
        if not hasattr(self._po_type, "deleted_at"):
            raise AttributeError(
                f"{self._po_type.__name__} does not support soft delete "
                "(missing 'deleted_at' field)"
            )

        stmt = (
            select(func.count())
            .select_from(self._po_type)
            .where(self._po_type.deleted_at.isnot(None))
        )

        if spec:
            stmt = spec.apply(stmt, self._po_type)

        result = await self._session.execute(stmt)

        return result.scalar() or 0

    async def is_trashed_po(self, id: Any) -> bool:
        """Check if an entity is soft-deleted.

        Args:
            id: Entity ID to check

        Returns:
            True if entity is soft-deleted, False otherwise

        Example:
            ```python
            if await repo.is_trashed_po(user_id):
                print("User is in trash")
            ```
        """
        if not hasattr(self._po_type, "deleted_at"):
            return False

        id_value = str(id.value) if hasattr(id, "value") else str(id)
        stmt = select(self._po_type.deleted_at).where(self._po_type.id == id_value).limit(1)

        result = await self._session.execute(stmt)

        deleted_at = result.scalar_one_or_none()
        return deleted_at is not None
