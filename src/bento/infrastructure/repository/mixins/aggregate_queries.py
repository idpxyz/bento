"""Aggregate Query Mixin for RepositoryAdapter.

Provides aggregate query operations at the Aggregate Root level:
- sum_field: Sum field values across aggregates
- avg_field: Average field values
- min_field: Minimum field value
- max_field: Maximum field value
- count_field: Count field values
"""

from __future__ import annotations

from typing import Any


class AggregateQueryMixin:
    """Mixin providing aggregate query operations for RepositoryAdapter.

    This mixin assumes the class has:
    - self._repository: BaseRepository instance
    """

    # Type hints for attributes provided by RepositoryAdapter
    _repository: Any  # BaseRepository instance
    _mapper: Any  # Mapper instance

    def _convert_spec_to_po(self, spec: Any) -> Any:  # type: ignore
        """Convert AR spec to PO spec (provided by RepositoryAdapter)."""
        ...

    async def sum_field(self, field: str, spec: Any | None = None) -> float:
        """Sum values of a field across all matching aggregates.

        Args:
            field: Field name to sum
            spec: Optional specification to filter aggregates

        Returns:
            Sum of field values (0 if no matches)

        Example:
            ```python
            # Total revenue from all orders
            total_revenue = await order_repo.sum_field("total")

            # Revenue from paid orders only
            paid_total = await order_repo.sum_field(
                "total",
                spec=OrderSpec().status_equals("PAID")
            )
            ```
        """
        # Convert AR spec to PO spec if needed
        po_spec = self._convert_spec_to_po(spec) if spec else None  # type: ignore
        return await self._repository.sum_field_po(field, po_spec)  # type: ignore

    async def avg_field(self, field: str, spec: Any | None = None) -> float:
        """Calculate average value of a field across all matching aggregates.

        Args:
            field: Field name to average
            spec: Optional specification to filter aggregates

        Returns:
            Average of field values (0 if no matches)

        Example:
            ```python
            # Average order value
            avg_order = await order_repo.avg_field("total")

            # Average price of active products
            avg_price = await product_repo.avg_field(
                "price",
                spec=ProductSpec().is_active()
            )
            ```
        """
        po_spec = self._convert_spec_to_po(spec) if spec else None  # type: ignore
        return await self._repository.avg_field_po(field, po_spec)  # type: ignore

    async def min_field(self, field: str, spec: Any | None = None) -> Any | None:
        """Find minimum value of a field across all matching aggregates.

        Args:
            field: Field name to find minimum
            spec: Optional specification to filter aggregates

        Returns:
            Minimum field value, or None if no matches

        Example:
            ```python
            # Lowest product price
            min_price = await product_repo.min_field("price")

            # Earliest order date for a customer
            earliest = await order_repo.min_field(
                "created_at",
                spec=OrderSpec().customer_id_equals("cust-123")
            )
            ```
        """
        po_spec = self._convert_spec_to_po(spec) if spec else None  # type: ignore
        return await self._repository.min_field_po(field, po_spec)  # type: ignore

    async def max_field(self, field: str, spec: Any | None = None) -> Any | None:
        """Find maximum value of a field across all matching aggregates.

        Args:
            field: Field name to find maximum
            spec: Optional specification to filter aggregates

        Returns:
            Maximum field value, or None if no matches

        Example:
            ```python
            # Highest product price
            max_price = await product_repo.max_field("price")

            # Latest order date
            latest = await order_repo.max_field("created_at")
            ```
        """
        po_spec = self._convert_spec_to_po(spec) if spec else None  # type: ignore
        return await self._repository.max_field_po(field, po_spec)  # type: ignore

    async def count_field(self, field: str, spec: Any | None = None, distinct: bool = False) -> int:
        """Count non-null values of a field.

        Args:
            field: Field name to count
            spec: Optional specification to filter aggregates
            distinct: If True, count only distinct values

        Returns:
            Count of non-null field values

        Example:
            ```python
            # Count orders with tracking number
            tracked_orders = await order_repo.count_field("tracking_number")

            # Count distinct customers who placed orders
            customer_count = await order_repo.count_field(
                "customer_id",
                distinct=True
            )
            ```
        """
        po_spec = self._convert_spec_to_po(spec) if spec else None  # type: ignore
        return await self._repository.count_field_po(field, po_spec, distinct)  # type: ignore
