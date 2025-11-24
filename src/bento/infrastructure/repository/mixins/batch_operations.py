"""Batch Operations Mixin for RepositoryAdapter.

Provides efficient batch ID operations at the Aggregate Root level:
- get_by_ids: Batch retrieve aggregates by IDs
- exists_by_id: Check if aggregate exists
- delete_by_ids: Batch delete aggregates by IDs
"""

from __future__ import annotations

from typing import Any


class BatchOperationsMixin:
    """Mixin providing batch ID operations for RepositoryAdapter.

    This mixin assumes the class has:
    - self._repository: BaseRepository instance
    - self._mapper: Mapper instance for AR <-> PO transformation
    """


    # Type hints for attributes provided by RepositoryAdapter
    _repository: Any  # BaseRepository instance
    _mapper: Any  # Mapper instance

    def _convert_spec_to_po(self, spec: Any) -> Any:  # type: ignore
        """Convert AR spec to PO spec (provided by RepositoryAdapter)."""
        ...

    async def get_by_ids(self, ids: list[Any]) -> list[Any]:
        """Get multiple aggregates by their IDs.

        Args:
            ids: List of entity IDs

        Returns:
            List of aggregates (may be shorter than ids if some not found)

        Example:
            ```python
            product_ids = [ID("p1"), ID("p2"), ID("p3")]
            products = await product_repo.get_by_ids(product_ids)
            ```
        """
        pos = await self._repository.get_po_by_ids(ids)  # type: ignore
        return self._mapper.map_reverse_list(pos)  # type: ignore

    async def exists_by_id(self, id: Any) -> bool:
        """Check if an aggregate exists by its ID.

        Args:
            id: Entity ID to check

        Returns:
            True if aggregate exists, False otherwise

        Example:
            ```python
            if await user_repo.exists_by_id(user_id):
                print("User exists")
            ```
        """
        return await self._repository.exists_po_by_id(id)  # type: ignore

    async def delete_by_ids(self, ids: list[Any]) -> int:
        """Delete multiple aggregates by their IDs.

        Note: This performs hard delete for performance. Does not load aggregates,
        so domain events will not be collected. Use delete() in a loop if you need events.

        Args:
            ids: List of entity IDs to delete

        Returns:
            Number of aggregates deleted

        Example:
            ```python
            expired_ids = [ID("o1"), ID("o2"), ID("o3")]
            count = await order_repo.delete_by_ids(expired_ids)
            print(f"Deleted {count} orders")
            ```
        """
        return await self._repository.delete_po_by_ids(ids)  # type: ignore
