"""Batch Operations Mixin for BaseRepository.

Provides efficient batch ID operations:
- get_po_by_ids: Batch retrieve by IDs
- exists_po_by_id: Check ID existence
- delete_by_ids: Batch delete by IDs
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import delete, select

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class BatchOperationsMixin:
    """Mixin providing batch ID operations for repositories.

    This mixin assumes the class has:
    - self._po_type: The persistence object type
    - self._session: AsyncSession instance
    """

    # Type hints for attributes provided by BaseRepository
    _po_type: type[Any]
    _session: AsyncSession

    async def get_po_by_ids(self, ids: list[Any]) -> list[Any]:
        """Get multiple persistence objects by their IDs.

        Args:
            ids: List of entity IDs

        Returns:
            List of persistence objects (may be shorter than ids if some not found)

        Example:
            ```python
            product_ids = [ID("p1"), ID("p2"), ID("p3")]
            products_po = await repo.get_po_by_ids(product_ids)
            ```
        """
        if not ids:
            return []

        # Convert IDs to strings for query
        id_values = [str(id.value) if hasattr(id, "value") else str(id) for id in ids]

        stmt = select(self._po_type).where(self._po_type.id.in_(id_values))

        result = await self._session.execute(stmt)

        return list(result.scalars().all())

    async def exists_po_by_id(self, id: Any) -> bool:
        """Check if a persistence object exists by its ID.

        Args:
            id: Entity ID to check

        Returns:
            True if entity exists, False otherwise

        Example:
            ```python
            if await repo.exists_po_by_id(user_id):
                print("User exists")
            ```
        """
        id_value = str(id.value) if hasattr(id, "value") else str(id)
        stmt = select(self._po_type.id).where(self._po_type.id == id_value).limit(1)
        result = await self._session.execute(stmt)

        return result.scalar_one_or_none() is not None

    async def delete_po_by_ids(self, ids: list[Any]) -> int:
        """Delete multiple persistence objects by their IDs.

        Note: This performs hard delete, bypassing interceptors for performance.
        For soft delete, use the regular delete() method in a loop.

        Args:
            ids: List of entity IDs to delete

        Returns:
            Number of entities deleted

        Example:
            ```python
            expired_order_ids = [ID("o1"), ID("o2"), ID("o3")]
            deleted_count = await repo.delete_po_by_ids(expired_order_ids)
            print(f"Deleted {deleted_count} orders")
            ```
        """
        if not ids:
            return 0

        id_values = [str(id.value) if hasattr(id, "value") else str(id) for id in ids]
        stmt = delete(self._po_type).where(self._po_type.id.in_(id_values))

        result = await self._session.execute(stmt)

        await self._session.flush()

        return result.rowcount
