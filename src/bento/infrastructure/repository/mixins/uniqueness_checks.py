"""Uniqueness Checks Mixin for RepositoryAdapter.

Provides field uniqueness validation at the Aggregate Root level:
- is_unique: Check if field value is unique
- find_by_field: Find aggregate by field value
- find_all_by_field: Find all aggregates by field value
"""

from __future__ import annotations

from typing import Any


class UniquenessChecksMixin:
    """Mixin providing uniqueness checks for RepositoryAdapter.

    This mixin assumes the class has:
    - self._repository: BaseRepository instance
    - self._mapper: Mapper instance for AR <-> PO transformation
    """

    # Type hints for attributes provided by RepositoryAdapter
    _repository: Any  # BaseRepository instance
    _mapper: Any  # Mapper instance

    def _convert_spec_to_po(self, spec: Any) -> Any:
        """Convert AR spec to PO spec (provided by RepositoryAdapter)."""
        ...

    async def is_unique(self, field: str, value: Any, exclude_id: Any | None = None) -> bool:
        """Check if a field value is unique across all aggregates.

        Args:
            field: Field name to check (must exist on both AR and PO)
            value: Value to check for uniqueness
            exclude_id: Optional ID to exclude from check (for updates)

        Returns:
            True if value is unique, False otherwise

        Example:
            ```python
            # Creating new user
            if not await user_repo.is_unique("email", "user@example.com"):
                raise ValidationError("Email already exists")

            # Updating user (exclude current ID)
            if not await user_repo.is_unique("email", new_email, exclude_id=user.id):
                raise ValidationError("Email already taken")
            ```
        """
        return await self._repository.is_field_unique_po(field, value, exclude_id)

    async def find_by_field(self, field: str, value: Any) -> Any | None:
        """Find a single aggregate by field value.

        Args:
            field: Field name to search (must exist on both AR and PO)
            value: Value to match

        Returns:
            First matching aggregate, or None if not found

        Example:
            ```python
            # Find user by email
            user = await user_repo.find_by_field("email", "admin@example.com")

            # Find product by SKU
            product = await product_repo.find_by_field("sku", "PROD-001")
            ```
        """
        po = await self._repository.find_po_by_field(field, value)

        if po is None:
            return None
        return self._mapper.map_reverse(po)

    async def find_all_by_field(self, field: str, value: Any) -> list[Any]:
        """Find all aggregates by field value.

        Args:
            field: Field name to search (must exist on both AR and PO)
            value: Value to match

        Returns:
            List of matching aggregates (may be empty)

        Example:
            ```python
            # Find all orders by customer
            orders = await order_repo.find_all_by_field("customer_id", "cust-123")

            # Find all products in category
            products = await product_repo.find_all_by_field("category_id", "cat-456")
            ```
        """
        pos = await self._repository.find_all_po_by_field(field, value)

        return self._mapper.map_reverse_list(pos)
