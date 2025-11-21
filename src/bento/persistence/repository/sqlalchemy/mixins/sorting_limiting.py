"""Sorting and Limiting Mixin for BaseRepository.

Provides sorting and limiting operations:
- find_first_po: Find first matching entity
- find_last_po: Find last matching entity
- find_top_n_po: Find top N entities
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import desc, select

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class SortingLimitingMixin:
    """Mixin providing sorting and limiting operations for repositories.

    This mixin assumes the class has:
    - self._po_type: The persistence object type
    - self._session: AsyncSession instance
    """

    # Type hints for attributes provided by BaseRepository
    _po_type: type[Any]
    _session: AsyncSession

    async def find_first_po(
        self, spec: Any | None = None, order_by: str | None = None
    ) -> Any | None:
        """Find first entity matching specification.

        Args:
            spec: Optional specification to filter entities
            order_by: Field name to sort by (prefix with '-' for descending)

        Returns:
            First matching entity, or None if no matches

        Example:
            ```python
            # First user
            first_user = await repo.find_first_po()

            # Latest order
            latest = await repo.find_first_po(order_by="-created_at")

            # First active product by name
            product = await repo.find_first_po(
                spec=ProductSpec().is_active(),
                order_by="name"
            )
            ```
        """
        stmt = select(self._po_type)  # type: ignore

        if spec:
            stmt = spec.apply(stmt, self._po_type)  # type: ignore

        if order_by:
            if order_by.startswith("-"):
                field_name = order_by[1:]
                stmt = stmt.order_by(desc(getattr(self._po_type, field_name)))  # type: ignore
            else:
                stmt = stmt.order_by(getattr(self._po_type, order_by))  # type: ignore

        stmt = stmt.limit(1)
        result = await self._session.execute(stmt)  # type: ignore
        return result.scalar_one_or_none()

    async def find_last_po(
        self, spec: Any | None = None, order_by: str = "created_at"
    ) -> Any | None:
        """Find last entity matching specification.

        Args:
            spec: Optional specification to filter entities
            order_by: Field name to sort by (default: "created_at")

        Returns:
            Last matching entity, or None if no matches

        Example:
            ```python
            # Latest order
            latest = await repo.find_last_po()

            # Most expensive product
            expensive = await repo.find_last_po(order_by="price")
            ```
        """
        # Reverse the order to get last
        reverse_order = f"-{order_by}" if not order_by.startswith("-") else order_by[1:]
        return await self.find_first_po(spec, reverse_order)

    async def find_top_n_po(
        self, n: int, spec: Any | None = None, order_by: str | None = None
    ) -> list[Any]:
        """Find top N entities matching specification.

        Args:
            n: Number of entities to return
            spec: Optional specification to filter entities
            order_by: Field name to sort by (prefix with '-' for descending)

        Returns:
            List of up to N matching entities

        Example:
            ```python
            # Top 10 products by price
            top_products = await repo.find_top_n_po(
                10,
                order_by="-price"
            )

            # Top 5 active users by registration date
            recent_users = await repo.find_top_n_po(
                5,
                spec=UserSpec().is_active(),
                order_by="-created_at"
            )
            ```
        """
        if n <= 0:
            return []

        stmt = select(self._po_type)  # type: ignore

        if spec:
            stmt = spec.apply(stmt, self._po_type)  # type: ignore

        if order_by:
            if order_by.startswith("-"):
                field_name = order_by[1:]
                stmt = stmt.order_by(desc(getattr(self._po_type, field_name)))  # type: ignore
            else:
                stmt = stmt.order_by(getattr(self._po_type, order_by))  # type: ignore

        stmt = stmt.limit(n)
        result = await self._session.execute(stmt)  # type: ignore
        return list(result.scalars().all())

    async def find_paginated_po(
        self,
        page: int = 1,
        page_size: int = 20,
        spec: Any | None = None,
        order_by: str | None = None,
    ) -> tuple[list[Any], int]:
        """Find entities with pagination.

        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page
            spec: Optional specification to filter entities
            order_by: Field name to sort by (prefix with '-' for descending)

        Returns:
            Tuple of (entities, total_count)

        Example:
            ```python
            # Page 1 of products
            products, total = await repo.find_paginated_po(
                page=1,
                page_size=20,
                order_by="name"
            )
            print(f"Showing {len(products)} of {total} products")
            ```
        """
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 20

        # Build base query
        stmt = select(self._po_type)  # type: ignore

        if spec:
            stmt = spec.apply(stmt, self._po_type)  # type: ignore

        # Get total count
        from sqlalchemy import func

        count_stmt = select(func.count()).select_from(self._po_type)  # type: ignore
        if spec:
            count_stmt = spec.apply(count_stmt, self._po_type)  # type: ignore
        count_result = await self._session.execute(count_stmt)  # type: ignore
        total = count_result.scalar() or 0

        # Apply sorting
        if order_by:
            if order_by.startswith("-"):
                field_name = order_by[1:]
                stmt = stmt.order_by(desc(getattr(self._po_type, field_name)))  # type: ignore
            else:
                stmt = stmt.order_by(getattr(self._po_type, order_by))  # type: ignore

        # Apply pagination
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        result = await self._session.execute(stmt)  # type: ignore
        entities = list(result.scalars().all())

        return entities, total
