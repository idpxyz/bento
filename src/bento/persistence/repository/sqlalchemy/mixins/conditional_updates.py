"""Conditional Update Mixin for BaseRepository.

Provides conditional update and delete operations:
- update_po_by_spec: Update entities matching specification
- delete_po_by_spec: Delete entities matching specification
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import delete, update

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class ConditionalUpdateMixin:
    """Mixin providing conditional update/delete operations for repositories.

    This mixin assumes the class has:
    - self._po_type: The persistence object type
    - self._session: AsyncSession instance
    - self._actor: Current actor for audit
    """

    # Type hints for attributes provided by BaseRepository
    _po_type: type[Any]
    _session: AsyncSession

    async def update_po_by_spec(self, spec: Any, updates: dict[str, Any]) -> int:
        """Update entities matching specification.

        Note: This performs bulk update, bypassing interceptors for performance.
        Use with caution - audit fields will not be automatically updated.

        Args:
            spec: Specification to filter entities
            updates: Dictionary of field:value pairs to update

        Returns:
            Number of entities updated

        Example:
            ```python
            # Cancel all pending orders older than 30 days
            spec = OrderSpec().status_equals("PENDING").older_than(days=30)
            count = await repo.update_po_by_spec(
                spec,
                {"status": "CANCELLED", "cancelled_at": datetime.now()}
            )
            print(f"Cancelled {count} orders")

            # Deactivate inactive users
            spec = UserSpec().last_login_before(days=180)
            await repo.update_po_by_spec(spec, {"is_active": False})
            ```
        """
        if not updates:
            return 0

        # Add updated_at and updated_by to updates if actor is available
        if hasattr(self, "_actor"):
            from datetime import datetime

            updates_copy = updates.copy()
            if hasattr(self._po_type, "updated_at"):
                updates_copy["updated_at"] = datetime.utcnow()
            if hasattr(self._po_type, "updated_by"):
                updates_copy["updated_by"] = self._actor

        else:
            updates_copy = updates

        # Build update statement
        stmt = update(self._po_type).values(**updates_copy)

        # Apply specification filter
        if spec:
            stmt = spec.apply(stmt, self._po_type)

        # Execute update
        result = await self._session.execute(stmt)

        await self._session.flush()

        return result.rowcount

    async def delete_po_by_spec(self, spec: Any) -> int:
        """Delete entities matching specification.

        Note: This performs hard delete, bypassing interceptors for performance.
        For soft delete, use the regular delete() method with specification.

        Args:
            spec: Specification to filter entities

        Returns:
            Number of entities deleted

        Example:
            ```python
            # Delete old log entries
            spec = LogSpec().older_than(days=90)
            count = await repo.delete_po_by_spec(spec)
            print(f"Deleted {count} old logs")

            # Delete cancelled orders
            spec = OrderSpec().status_equals("CANCELLED")
            await repo.delete_po_by_spec(spec)
            ```
        """
        # Build delete statement
        stmt = delete(self._po_type)

        # Apply specification filter
        if spec:
            stmt = spec.apply(stmt, self._po_type)

        # Execute delete
        result = await self._session.execute(stmt)

        await self._session.flush()

        return result.rowcount

    async def soft_delete_po_by_spec(self, spec: Any) -> int:
        """Soft delete entities matching specification.

        Sets deleted_at and deleted_by fields instead of removing records.

        Args:
            spec: Specification to filter entities

        Returns:
            Number of entities soft-deleted

        Example:
            ```python
            # Soft delete inactive users
            spec = UserSpec().is_inactive()
            count = await repo.soft_delete_po_by_spec(spec)
            print(f"Soft deleted {count} users")
            ```
        """
        from datetime import datetime

        # Check if soft delete fields exist
        if not hasattr(self._po_type, "deleted_at"):
            raise AttributeError(
                f"{self._po_type.__name__} does not support soft delete "
                "(missing 'deleted_at' field)"
            )

        updates = {"deleted_at": datetime.utcnow()}
        if hasattr(self._po_type, "deleted_by") and hasattr(self, "_actor"):
            updates["deleted_by"] = self._actor

        return await self.update_po_by_spec(spec, updates)

    async def restore_po_by_spec(self, spec: Any) -> int:
        """Restore soft-deleted entities matching specification.

        Clears deleted_at and deleted_by fields.

        Args:
            spec: Specification to filter entities

        Returns:
            Number of entities restored

        Example:
            ```python
            # Restore recently deleted users
            spec = UserSpec().deleted_after(days=7)
            count = await repo.restore_po_by_spec(spec)
            print(f"Restored {count} users")
            ```
        """
        # Check if soft delete fields exist
        if not hasattr(self._po_type, "deleted_at"):
            raise AttributeError(
                f"{self._po_type.__name__} does not support soft delete "
                "(missing 'deleted_at' field)"
            )

        updates = {"deleted_at": None}
        if hasattr(self._po_type, "deleted_by"):
            updates["deleted_by"] = None

        return await self.update_po_by_spec(spec, updates)
