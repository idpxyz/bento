"""Conditional Update Mixin for RepositoryAdapter.

Provides conditional update and delete operations at the Aggregate Root level:
- update_by_spec: Update aggregates matching specification
- delete_by_spec: Delete aggregates matching specification
- soft_delete_by_spec: Soft delete aggregates
- restore_by_spec: Restore soft-deleted aggregates
"""

from __future__ import annotations

from typing import Any


class ConditionalUpdateMixin:
    """Mixin providing conditional update/delete operations for RepositoryAdapter.

    This mixin assumes the class has:
    - self._repository: BaseRepository instance
    - self._convert_spec_to_po: Method to convert AR spec to PO spec
    """

    # Type hints for attributes provided by RepositoryAdapter
    _repository: Any  # BaseRepository instance
    _mapper: Any  # Mapper instance

    def _convert_spec_to_po(self, spec: Any) -> Any:  # type: ignore
        """Convert AR spec to PO spec (provided by RepositoryAdapter)."""
        ...

    async def update_by_spec(self, spec: Any, updates: dict[str, Any]) -> int:
        """Update aggregates matching specification.

        Note: This performs bulk update for performance. Does not load aggregates,
        so domain events will not be collected. Use regular save() if you need events.

        Args:
            spec: Specification to filter aggregates
            updates: Dictionary of field:value pairs to update

        Returns:
            Number of aggregates updated

        Example:
            ```python
            # Cancel all pending orders older than 30 days
            from datetime import datetime, timedelta

            spec = OrderSpec().status_equals("PENDING").created_before(
                datetime.now() - timedelta(days=30)
            )
            count = await order_repo.update_by_spec(
                spec,
                {"status": "CANCELLED", "cancelled_at": datetime.now()}
            )
            print(f"Cancelled {count} orders")

            # Deactivate inactive users
            spec = UserSpec().last_login_before(days=180)
            await user_repo.update_by_spec(spec, {"is_active": False})
            ```
        """
        po_spec = self._convert_spec_to_po(spec)  # type: ignore
        return await self._repository.update_po_by_spec(po_spec, updates)  # type: ignore

    async def delete_by_spec(self, spec: Any) -> int:
        """Delete aggregates matching specification.

        Note: This performs hard delete for performance. Does not load aggregates,
        so domain events will not be collected. Use delete() in a loop if you need events.

        Args:
            spec: Specification to filter aggregates

        Returns:
            Number of aggregates deleted

        Example:
            ```python
            # Delete old log entries
            spec = LogSpec().older_than(days=90)
            count = await log_repo.delete_by_spec(spec)
            print(f"Deleted {count} old logs")

            # Delete cancelled orders
            spec = OrderSpec().status_equals("CANCELLED")
            await order_repo.delete_by_spec(spec)
            ```
        """
        po_spec = self._convert_spec_to_po(spec)  # type: ignore
        return await self._repository.delete_po_by_spec(po_spec)  # type: ignore

    async def soft_delete_by_spec(self, spec: Any) -> int:
        """Soft delete aggregates matching specification.

        Sets deleted_at and deleted_by fields instead of removing records.

        Args:
            spec: Specification to filter aggregates

        Returns:
            Number of aggregates soft-deleted

        Example:
            ```python
            # Soft delete inactive users
            spec = UserSpec().is_inactive()
            count = await user_repo.soft_delete_by_spec(spec)
            print(f"Soft deleted {count} users")

            # Soft delete expired sessions
            spec = SessionSpec().expired()
            await session_repo.soft_delete_by_spec(spec)
            ```
        """
        po_spec = self._convert_spec_to_po(spec)  # type: ignore
        return await self._repository.soft_delete_po_by_spec(po_spec)  # type: ignore

    async def restore_by_spec(self, spec: Any) -> int:
        """Restore soft-deleted aggregates matching specification.

        Clears deleted_at and deleted_by fields.

        Args:
            spec: Specification to filter aggregates

        Returns:
            Number of aggregates restored

        Example:
            ```python
            # Restore recently deleted users
            spec = UserSpec().deleted_within_days(7)
            count = await user_repo.restore_by_spec(spec)
            print(f"Restored {count} users")

            # Restore accidentally deleted orders
            spec = OrderSpec().deleted_by("admin").deleted_today()
            await order_repo.restore_by_spec(spec)
            ```
        """
        po_spec = self._convert_spec_to_po(spec)  # type: ignore
        return await self._repository.restore_po_by_spec(po_spec)  # type: ignore
