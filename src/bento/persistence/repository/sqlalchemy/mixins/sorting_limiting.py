"""Sorting and Limiting Mixin for BaseRepository.

Provides sorting and limiting operations:
- find_first_po: Find first matching entity
- find_last_po: Find last matching entity
- find_top_n_po: Find top N entities
- find_paginated_po: Find entities with pagination

With caching support via CacheInterceptor.
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
    - self._interceptor_chain: Optional interceptor chain for caching
    - self._actor: Actor performing the operation
    """

    # Type hints for attributes provided by BaseRepository
    _po_type: type[Any]
    _session: AsyncSession
    _interceptor_chain: Any  # InterceptorChain[Any] | None
    _actor: str

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
        # Try interceptor cache first
        context = None
        if self._interceptor_chain:
            from bento.persistence.interceptor import InterceptorContext, OperationType

            context = InterceptorContext(
                session=self._session,
                entity_type=self._po_type,
                operation=OperationType.SORT_LIMIT,
                actor=self._actor,
                context_data={
                    "method": "first",
                    "order_by": order_by or "",
                    "limit": 1,
                    "specification": spec,
                },
            )
            cached = await self._interceptor_chain.execute_before(context)
            if cached is not None:
                return cached

        # Execute query
        stmt = select(self._po_type)

        if spec:
            stmt = spec.apply(stmt, self._po_type)

        if order_by:
            if order_by.startswith("-"):
                field_name = order_by[1:]
                stmt = stmt.order_by(desc(getattr(self._po_type, field_name)))

            else:
                stmt = stmt.order_by(getattr(self._po_type, order_by))

        stmt = stmt.limit(1)
        result = await self._session.execute(stmt)

        result_value = result.scalar_one_or_none()

        # Process result through interceptor (for caching)
        if self._interceptor_chain and context is not None:
            result_value = await self._interceptor_chain.process_result(context, result_value)

        return result_value

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

        # Try interceptor cache first
        context = None
        if self._interceptor_chain:
            from bento.persistence.interceptor import InterceptorContext, OperationType

            context = InterceptorContext(
                session=self._session,
                entity_type=self._po_type,
                operation=OperationType.SORT_LIMIT,
                actor=self._actor,
                context_data={
                    "method": "top_n",
                    "order_by": order_by or "",
                    "limit": n,
                    "specification": spec,
                },
            )
            cached = await self._interceptor_chain.execute_before(context)
            if cached is not None:
                return cached

        # Execute query
        stmt = select(self._po_type)

        if spec:
            stmt = spec.apply(stmt, self._po_type)

        if order_by:
            if order_by.startswith("-"):
                field_name = order_by[1:]
                stmt = stmt.order_by(desc(getattr(self._po_type, field_name)))

            else:
                stmt = stmt.order_by(getattr(self._po_type, order_by))

        stmt = stmt.limit(n)
        result = await self._session.execute(stmt)

        result_value = list(result.scalars().all())

        # Process result through interceptor (for caching)
        if self._interceptor_chain and context is not None:
            result_value = await self._interceptor_chain.process_result(context, result_value)

        return result_value

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

        # Try interceptor cache first
        context = None
        if self._interceptor_chain:
            from bento.persistence.interceptor import InterceptorContext, OperationType

            context = InterceptorContext(
                session=self._session,
                entity_type=self._po_type,
                operation=OperationType.PAGINATE,
                actor=self._actor,
                context_data={
                    "page": page,
                    "page_size": page_size,
                    "order_by": order_by or "",
                    "specification": spec,
                },
            )
            cached = await self._interceptor_chain.execute_before(context)
            if cached is not None:
                return cached

        # Execute query
        # Build base query
        stmt = select(self._po_type)

        if spec:
            stmt = spec.apply(stmt, self._po_type)

        # Get total count
        from sqlalchemy import func

        count_stmt = select(func.count()).select_from(self._po_type)

        if spec:
            count_stmt = spec.apply(count_stmt, self._po_type)

        count_result = await self._session.execute(count_stmt)

        total = count_result.scalar() or 0

        # Apply sorting
        if order_by:
            if order_by.startswith("-"):
                field_name = order_by[1:]
                stmt = stmt.order_by(desc(getattr(self._po_type, field_name)))

            else:
                stmt = stmt.order_by(getattr(self._po_type, order_by))

        # Apply pagination
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        result = await self._session.execute(stmt)

        entities = list(result.scalars().all())
        result_value = (entities, total)

        # Process result through interceptor (for caching)
        if self._interceptor_chain and context is not None:
            result_value = await self._interceptor_chain.process_result(context, result_value)

        return result_value
