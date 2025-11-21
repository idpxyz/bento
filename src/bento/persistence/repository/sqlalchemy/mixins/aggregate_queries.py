"""Aggregate Query Mixin for BaseRepository.

Provides aggregate query operations:
- sum_field_po: Sum field values
- avg_field_po: Average field values
- min_field_po: Minimum field value
- max_field_po: Maximum field value
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class AggregateQueryMixin:
    """Mixin providing aggregate query operations for repositories.

    This mixin assumes the class has:
    - self._po_type: The persistence object type
    - self._session: AsyncSession instance
    """

    # Type hints for attributes provided by BaseRepository
    _po_type: type[Any]
    _session: AsyncSession

    async def sum_field_po(self, field: str, spec: Any | None = None) -> float:
        """Sum values of a field across all matching entities.

        Args:
            field: Field name to sum
            spec: Optional specification to filter entities

        Returns:
            Sum of field values (0 if no matches)

        Example:
            ```python
            # Total revenue
            total = await repo.sum_field_po("total")

            # Revenue for paid orders
            paid_total = await repo.sum_field_po("total", OrderSpec().status("PAID"))
            ```
        """
        stmt = select(func.sum(getattr(self._po_type, field)))  # type: ignore

        if spec:
            stmt = spec.apply(stmt, self._po_type)  # type: ignore

        result = await self._session.execute(stmt)  # type: ignore
        value = result.scalar()
        return float(value) if value is not None else 0.0

    async def avg_field_po(self, field: str, spec: Any | None = None) -> float:
        """Calculate average value of a field across all matching entities.

        Args:
            field: Field name to average
            spec: Optional specification to filter entities

        Returns:
            Average of field values (0 if no matches)

        Example:
            ```python
            # Average order value
            avg_order = await repo.avg_field_po("total")

            # Average price of active products
            avg_price = await repo.avg_field_po("price", ProductSpec().is_active())
            ```
        """
        stmt = select(func.avg(getattr(self._po_type, field)))  # type: ignore

        if spec:
            stmt = spec.apply(stmt, self._po_type)  # type: ignore

        result = await self._session.execute(stmt)  # type: ignore
        value = result.scalar()
        return float(value) if value is not None else 0.0

    async def min_field_po(self, field: str, spec: Any | None = None) -> Any | None:
        """Find minimum value of a field across all matching entities.

        Args:
            field: Field name to find minimum
            spec: Optional specification to filter entities

        Returns:
            Minimum field value, or None if no matches

        Example:
            ```python
            # Lowest price
            min_price = await repo.min_field_po("price")

            # Earliest order date
            earliest = await repo.min_field_po("created_at")
            ```
        """
        stmt = select(func.min(getattr(self._po_type, field)))  # type: ignore

        if spec:
            stmt = spec.apply(stmt, self._po_type)  # type: ignore

        result = await self._session.execute(stmt)  # type: ignore
        return result.scalar()

    async def max_field_po(self, field: str, spec: Any | None = None) -> Any | None:
        """Find maximum value of a field across all matching entities.

        Args:
            field: Field name to find maximum
            spec: Optional specification to filter entities

        Returns:
            Maximum field value, or None if no matches

        Example:
            ```python
            # Highest price
            max_price = await repo.max_field_po("price")

            # Latest order date
            latest = await repo.max_field_po("created_at")
            ```
        """
        stmt = select(func.max(getattr(self._po_type, field)))  # type: ignore

        if spec:
            stmt = spec.apply(stmt, self._po_type)  # type: ignore

        result = await self._session.execute(stmt)  # type: ignore
        return result.scalar()

    async def count_field_po(
        self, field: str, spec: Any | None = None, distinct: bool = False
    ) -> int:
        """Count non-null values of a field.

        Args:
            field: Field name to count
            spec: Optional specification to filter entities
            distinct: If True, count only distinct values

        Returns:
            Count of non-null field values

        Example:
            ```python
            # Count orders with tracking number
            tracked = await repo.count_field_po("tracking_number")

            # Count distinct customers
            customers = await repo.count_field_po("customer_id", distinct=True)
            ```
        """
        field_obj = getattr(self._po_type, field)  # type: ignore
        if distinct:
            stmt = select(func.count(func.distinct(field_obj)))
        else:
            stmt = select(func.count(field_obj))

        if spec:
            stmt = spec.apply(stmt, self._po_type)  # type: ignore

        result = await self._session.execute(stmt)  # type: ignore
        return result.scalar() or 0
