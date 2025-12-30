"""Group By Query Mixin for BaseRepository.

Provides group by and aggregation operations:
- group_by_field_po: Group and count by field
- group_by_date_po: Group and count by date
- group_by_multiple_fields_po: Group by multiple fields

With caching support via CacheInterceptor.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import extract, func, select

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class GroupByQueryMixin:
    """Mixin providing group by query operations for repositories.

    This mixin assumes the class has:
    - self._po_type: The persistence object type
    - self._session: AsyncSession instance
    - self._interceptor_chain: Optional interceptor chain for caching
    - self._actor: Actor performing the operation
    """

    # Type hints for attributes provided by BaseRepository
    _po_type: type[Any]
    _session: AsyncSession
    _interceptor_chain: Any  # InterceptorChain[Any] | None
    _actor: str

    async def group_by_field_po(self, field: str, spec: Any | None = None) -> dict[Any, int]:
        """Group entities by field and count each group.

        Args:
            field: Field name to group by
            spec: Optional specification to filter entities

        Returns:
            Dictionary mapping field values to counts

        Example:
            ```python
            # Count orders by status
            status_counts = await repo.group_by_field_po("status")
            # Result: {"PENDING": 10, "PAID": 25, "SHIPPED": 15}

            # Count products by category
            category_counts = await repo.group_by_field_po("category_id")
            # Result: {"cat-1": 50, "cat-2": 30}
            ```
        """
        # Try interceptor cache first
        context = None
        if self._interceptor_chain:
            from bento.persistence.interceptor import InterceptorContext, OperationType

            context = InterceptorContext(
                session=self._session,

                entity_type=self._po_type,
                operation=OperationType.GROUP_BY,
                actor=self._actor,
                context_data={
                    "group_fields": [field],
                    "specification": spec,
                },
            )
            cached = await self._interceptor_chain.execute_before(context)
            if cached is not None:
                return cached

        # Execute query
        field_obj = getattr(self._po_type, field)

        stmt = select(field_obj, func.count().label("count")).group_by(field_obj)

        if spec:
            stmt = spec.apply(stmt, self._po_type)


        result = await self._session.execute(stmt)

        rows = result.all()
        result_value = {row[0]: row[1] for row in rows}

        # Process result through interceptor (for caching)
        if self._interceptor_chain and context is not None:
            result_value = await self._interceptor_chain.process_result(context, result_value)

        return result_value

    async def group_by_date_po(
        self, date_field: str, granularity: str = "day", spec: Any | None = None
    ) -> dict[str, int]:
        """Group entities by date and count each group.

        Args:
            date_field: Date/datetime field name to group by
            granularity: Grouping granularity: "day", "week", "month", "year"
            spec: Optional specification to filter entities

        Returns:
            Dictionary mapping date strings to counts

        Example:
            ```python
            # Count orders by day
            daily = await repo.group_by_date_po("created_at", "day")
            # Result: {"2025-01-01": 5, "2025-01-02": 8, ...}

            # Count orders by month
            monthly = await repo.group_by_date_po("created_at", "month")
            # Result: {"2025-01": 150, "2025-02": 180, ...}
            ```
        """
        # Try interceptor cache first
        context = None
        if self._interceptor_chain:
            from bento.persistence.interceptor import InterceptorContext, OperationType

            context = InterceptorContext(
                session=self._session,

                entity_type=self._po_type,
                operation=OperationType.GROUP_BY,
                actor=self._actor,
                context_data={
                    "group_fields": [date_field],
                    "period": granularity,
                    "specification": spec,
                },
            )
            cached = await self._interceptor_chain.execute_before(context)
            if cached is not None:
                return cached

        # Execute query
        field_obj = getattr(self._po_type, date_field)


        if granularity == "day":
            # Group by date (YYYY-MM-DD) using strftime for SQLite compatibility
            date_expr = func.date(field_obj)
            stmt = select(date_expr, func.count().label("count")).group_by(date_expr)

        elif granularity == "week":
            # Group by year-week
            year = extract("year", field_obj)
            week = extract("week", field_obj)
            stmt = select(year, week, func.count().label("count")).group_by(year, week)

        elif granularity == "month":
            # Group by year-month
            year = extract("year", field_obj)
            month = extract("month", field_obj)
            stmt = select(year, month, func.count().label("count")).group_by(year, month)

        elif granularity == "year":
            # Group by year
            year = extract("year", field_obj)
            stmt = select(year, func.count().label("count")).group_by(year)

        else:
            raise ValueError(
                f"Invalid granularity: {granularity}. Must be one of: day, week, month, year"
            )

        if spec:
            stmt = spec.apply(stmt, self._po_type)


        result = await self._session.execute(stmt)

        rows = result.all()

        # Format results based on granularity
        if granularity == "day":
            # func.date() returns string directly
            result_value = {str(row[0]): row[1] for row in rows}
        elif granularity == "week":
            result_value = {f"{int(row[0])}-W{int(row[1]):02d}": row[2] for row in rows}
        elif granularity == "month":
            result_value = {f"{int(row[0])}-{int(row[1]):02d}": row[2] for row in rows}
        elif granularity == "year":
            result_value = {str(int(row[0])): row[1] for row in rows}
        else:
            result_value = {}

        # Process result through interceptor (for caching)
        if self._interceptor_chain and context is not None:
            result_value = await self._interceptor_chain.process_result(context, result_value)

        return result_value

    async def group_by_multiple_fields_po(
        self, fields: list[str], spec: Any | None = None
    ) -> dict[tuple, int]:
        """Group entities by multiple fields and count each group.

        Args:
            fields: List of field names to group by
            spec: Optional specification to filter entities

        Returns:
            Dictionary mapping field value tuples to counts

        Example:
            ```python
            # Count orders by status and customer
            counts = await repo.group_by_multiple_fields_po(
                ["status", "customer_id"]
            )
            # Result: {("PENDING", "c1"): 3, ("PAID", "c1"): 5, ...}
            ```
        """
        if not fields:
            raise ValueError("At least one field is required for grouping")

        # Try interceptor cache first
        context = None
        if self._interceptor_chain:
            from bento.persistence.interceptor import InterceptorContext, OperationType

            context = InterceptorContext(
                session=self._session,

                entity_type=self._po_type,
                operation=OperationType.GROUP_BY,
                actor=self._actor,
                context_data={
                    "group_fields": fields,
                    "specification": spec,
                },
            )
            cached = await self._interceptor_chain.execute_before(context)
            if cached is not None:
                return cached

        # Execute query
        field_objs = [
            getattr(self._po_type, f)
            for f in fields

        ]

        stmt = select(*field_objs, func.count().label("count")).group_by(*field_objs)

        if spec:
            stmt = spec.apply(stmt, self._po_type)


        result = await self._session.execute(stmt)

        rows = result.all()
        result_value = {tuple(row[:-1]): row[-1] for row in rows}

        # Process result through interceptor (for caching)
        if self._interceptor_chain and context is not None:
            result_value = await self._interceptor_chain.process_result(context, result_value)

        return result_value
