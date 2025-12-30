"""Sorting and Limiting Mixin for RepositoryAdapter.

Provides sorting and limiting operations at the Aggregate Root level:
- find_first: Find first matching aggregate
- find_last: Find last matching aggregate
- find_top_n: Find top N aggregates
- find_paginated: Paginated query
"""

from __future__ import annotations

from typing import Any


class SortingLimitingMixin:
    """Mixin providing sorting and limiting operations for RepositoryAdapter.

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

    async def find_first(self, spec: Any | None = None, order_by: str | None = None) -> Any | None:
        """Find first aggregate matching specification.

        Args:
            spec: Optional specification to filter aggregates
            order_by: Field name to sort by (prefix with '-' for descending)

        Returns:
            First matching aggregate, or None if no matches

        Example:
            ```python
            # First user
            first_user = await user_repo.find_first()

            # Latest order
            latest = await order_repo.find_first(order_by="-created_at")

            # First active product by name
            product = await product_repo.find_first(
                spec=ProductSpec().is_active(),
                order_by="name"
            )
            ```
        """
        po_spec = self._convert_spec_to_po(spec) if spec else None  # type: ignore
        po = await self._repository.find_first_po(po_spec, order_by)  # type: ignore
        if po is None:
            return None
        return self._mapper.map_reverse(po)  # type: ignore

    async def find_last(self, spec: Any | None = None, order_by: str = "created_at") -> Any | None:
        """Find last aggregate matching specification.

        Args:
            spec: Optional specification to filter aggregates
            order_by: Field name to sort by (default: "created_at")

        Returns:
            Last matching aggregate, or None if no matches

        Example:
            ```python
            # Latest order
            latest = await order_repo.find_last()

            # Most expensive product
            expensive = await product_repo.find_last(order_by="price")
            ```
        """
        po_spec = self._convert_spec_to_po(spec) if spec else None  # type: ignore
        po = await self._repository.find_last_po(po_spec, order_by)  # type: ignore
        if po is None:
            return None
        return self._mapper.map_reverse(po)  # type: ignore

    async def find_top_n(
        self, n: int, spec: Any | None = None, order_by: str | None = None
    ) -> list[Any]:
        """Find top N aggregates matching specification.

        Args:
            n: Number of aggregates to return
            spec: Optional specification to filter aggregates
            order_by: Field name to sort by (prefix with '-' for descending)

        Returns:
            List of up to N matching aggregates

        Example:
            ```python
            # Top 10 products by price
            top_products = await product_repo.find_top_n(10, order_by="-price")

            # Top 5 recent active users
            recent_users = await user_repo.find_top_n(
                5,
                spec=UserSpec().is_active(),
                order_by="-created_at"
            )
            ```
        """
        po_spec = self._convert_spec_to_po(spec) if spec else None  # type: ignore
        pos = await self._repository.find_top_n_po(n, po_spec, order_by)  # type: ignore
        return self._mapper.map_reverse_list(pos)  # type: ignore

    async def find_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        spec: Any | None = None,
        order_by: str | None = None,
    ) -> tuple[list[Any], int]:
        """Find aggregates with pagination.

        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page
            spec: Optional specification to filter aggregates
            order_by: Field name to sort by (prefix with '-' for descending)

        Returns:
            Tuple of (aggregates, total_count)

        Example:
            ```python
            # Page 1 of products
            products, total = await product_repo.find_paginated(
                page=1,
                page_size=20,
                order_by="name"
            )
            print(f"Showing {len(products)} of {total} products")

            # Page 2 of orders for a customer
            orders, total = await order_repo.find_paginated(
                page=2,
                page_size=10,
                spec=OrderSpec().customer_id_equals("cust-123"),
                order_by="-created_at"
            )
            ```
        """
        po_spec = self._convert_spec_to_po(spec) if spec else None  # type: ignore
        pos, total = await self._repository.find_paginated_po(  # type: ignore
            page, page_size, po_spec, order_by
        )
        aggregates = self._mapper.map_reverse_list(pos)  # type: ignore
        return aggregates, total
