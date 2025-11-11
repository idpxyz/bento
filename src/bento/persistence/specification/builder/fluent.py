"""Fluent Specification Builder - Legend-style chainable query builder.

This module provides a fluent, chainable API for building Specification objects,
inspired by Legend's query builder while maintaining Bento's type safety and
architectural principles.

Features:
    - Chainable API for intuitive query building
    - Type-safe filter operations
    - Automatic soft-delete handling
    - Ordering and pagination support
    - Full integration with Bento's Specification system

Example:
    ```python
    # Simple query
    spec = (
        FluentBuilder(OrderModel)
        .equals("status", "pending")
        .greater_than("total_amount", 100)
        .order_by("created_at", descending=True)
        .build()
    )

    # Complex query with multiple conditions
    spec = (
        FluentBuilder(ProductModel)
        .in_("category", ["electronics", "books"])
        .greater_than("price", 50)
        .less_than("price", 200)
        .like("name", "%laptop%")
        .order_by("price")
        .limit(10)
        .build()
    )

    # Include soft-deleted records
    spec = (
        FluentBuilder(OrderModel)
        .equals("customer_id", "customer-123")
        .include_deleted()
        .build()
    )
    ```

Design:
    - Builds on top of EntitySpecification (composition over inheritance)
    - Maintains type safety through generic typing
    - Returns self for method chaining
    - Converts to standard Specification via build()
"""

from typing import Any

from bento.persistence.specification.core.base import CompositeSpecification
from bento.persistence.specification.core.types import Filter, FilterOperator, PageParams, Sort


class FluentSpecificationBuilder[T]:
    """Fluent builder for creating Specification objects with chainable API.

    This builder provides a more intuitive, Legend-style API for creating
    specifications while maintaining full compatibility with Bento's
    Specification system.

    Type Parameters:
        T: The entity/model type this builder creates specifications for

    Example:
        ```python
        # Create builder for OrderModel
        builder = FluentSpecificationBuilder(OrderModel)

        # Chain conditions
        spec = (
            builder
            .equals("status", "pending")
            .greater_than("total_amount", 100)
            .order_by("created_at")
            .build()
        )

        # Use with repository
        orders = await repo.find_many(spec)
        ```

    Note:
        - All methods return self for chaining
        - Call build() to get the final Specification
        - By default, excludes soft-deleted records (deleted_at IS NULL)
        - Use include_deleted() or only_deleted() to change this behavior
    """

    def __init__(self, entity_type: type[T]) -> None:
        """Initialize fluent builder.

        Args:
            entity_type: The entity/model class this builder is for

        Example:
            ```python
            builder = FluentSpecificationBuilder(OrderModel)
            ```
        """
        self._entity_type = entity_type
        self._filters: list[Filter] = []
        self._sorts: list[Sort] = []
        self._limit_value: int | None = None
        self._offset_value: int | None = None
        self._include_deleted: bool = False
        self._only_deleted: bool = False

    # ============================================================================
    # Comparison Operators
    # ============================================================================

    def equals(self, field: str, value: Any) -> "FluentSpecificationBuilder[T]":
        """Add equality filter (field = value).

        Args:
            field: Field name to filter on
            value: Value to match

        Returns:
            Self for chaining

        Example:
            ```python
            builder.equals("status", "pending")
            builder.equals("customer_id", "customer-123")
            ```
        """
        self._filters.append(Filter(field=field, operator=FilterOperator.EQUALS, value=value))
        return self

    def not_equals(self, field: str, value: Any) -> "FluentSpecificationBuilder[T]":
        """Add not-equals filter (field != value).

        Args:
            field: Field name to filter on
            value: Value to exclude

        Returns:
            Self for chaining

        Example:
            ```python
            builder.not_equals("status", "cancelled")
            ```
        """
        self._filters.append(Filter(field=field, operator=FilterOperator.NOT_EQUALS, value=value))
        return self

    def greater_than(self, field: str, value: Any) -> "FluentSpecificationBuilder[T]":
        """Add greater-than filter (field > value).

        Args:
            field: Field name to filter on
            value: Minimum value (exclusive)

        Returns:
            Self for chaining

        Example:
            ```python
            builder.greater_than("total_amount", 100)
            builder.greater_than("created_at", yesterday)
            ```
        """
        self._filters.append(Filter(field=field, operator=FilterOperator.GREATER_THAN, value=value))
        return self

    def greater_than_or_equal(self, field: str, value: Any) -> "FluentSpecificationBuilder[T]":
        """Add greater-than-or-equal filter (field >= value).

        Args:
            field: Field name to filter on
            value: Minimum value (inclusive)

        Returns:
            Self for chaining

        Example:
            ```python
            builder.greater_than_or_equal("total_amount", 100)
            ```
        """
        self._filters.append(
            Filter(field=field, operator=FilterOperator.GREATER_EQUAL, value=value)
        )
        return self

    def less_than(self, field: str, value: Any) -> "FluentSpecificationBuilder[T]":
        """Add less-than filter (field < value).

        Args:
            field: Field name to filter on
            value: Maximum value (exclusive)

        Returns:
            Self for chaining

        Example:
            ```python
            builder.less_than("total_amount", 1000)
            builder.less_than("created_at", tomorrow)
            ```
        """
        self._filters.append(Filter(field=field, operator=FilterOperator.LESS_THAN, value=value))
        return self

    def less_than_or_equal(self, field: str, value: Any) -> "FluentSpecificationBuilder[T]":
        """Add less-than-or-equal filter (field <= value).

        Args:
            field: Field name to filter on
            value: Maximum value (inclusive)

        Returns:
            Self for chaining

        Example:
            ```python
            builder.less_than_or_equal("total_amount", 1000)
            ```
        """
        self._filters.append(Filter(field=field, operator=FilterOperator.LESS_EQUAL, value=value))
        return self

    def in_(self, field: str, values: list[Any]) -> "FluentSpecificationBuilder[T]":
        """Add IN filter (field IN (values)).

        Args:
            field: Field name to filter on
            values: List of acceptable values

        Returns:
            Self for chaining

        Example:
            ```python
            builder.in_("status", ["pending", "processing"])
            builder.in_("category_id", [1, 2, 3])
            ```

        Note:
            Use trailing underscore to avoid conflict with Python keyword.
        """
        self._filters.append(Filter(field=field, operator=FilterOperator.IN, value=values))
        return self

    def not_in(self, field: str, values: list[Any]) -> "FluentSpecificationBuilder[T]":
        """Add NOT IN filter (field NOT IN (values)).

        Args:
            field: Field name to filter on
            values: List of values to exclude

        Returns:
            Self for chaining

        Example:
            ```python
            builder.not_in("status", ["cancelled", "failed"])
            ```
        """
        self._filters.append(Filter(field=field, operator=FilterOperator.NOT_IN, value=values))
        return self

    def like(self, field: str, pattern: str) -> "FluentSpecificationBuilder[T]":
        """Add LIKE filter (field LIKE pattern).

        Args:
            field: Field name to filter on
            pattern: SQL LIKE pattern (use % as wildcard)

        Returns:
            Self for chaining

        Example:
            ```python
            builder.like("name", "%laptop%")
            builder.like("email", "%@example.com")
            ```

        Note:
            Pattern is case-sensitive (database-dependent).
        """
        self._filters.append(Filter(field=field, operator=FilterOperator.LIKE, value=pattern))
        return self

    def is_null(self, field: str) -> "FluentSpecificationBuilder[T]":
        """Add IS NULL filter (field IS NULL).

        Args:
            field: Field name to check

        Returns:
            Self for chaining

        Example:
            ```python
            builder.is_null("deleted_at")  # Not deleted
            builder.is_null("paid_at")     # Not paid
            ```
        """
        self._filters.append(Filter(field=field, operator=FilterOperator.IS_NULL, value=None))
        return self

    def is_not_null(self, field: str) -> "FluentSpecificationBuilder[T]":
        """Add IS NOT NULL filter (field IS NOT NULL).

        Args:
            field: Field name to check

        Returns:
            Self for chaining

        Example:
            ```python
            builder.is_not_null("paid_at")      # Is paid
            builder.is_not_null("deleted_at")   # Is deleted
            ```
        """
        self._filters.append(Filter(field=field, operator=FilterOperator.IS_NOT_NULL, value=None))
        return self

    # ============================================================================
    # Soft Delete Handling
    # ============================================================================

    def include_deleted(self) -> "FluentSpecificationBuilder[T]":
        """Include soft-deleted records in results.

        By default, FluentBuilder excludes soft-deleted records (deleted_at IS NULL).
        This method includes them.

        Returns:
            Self for chaining

        Example:
            ```python
            # Include both active and deleted orders
            builder.equals("customer_id", "customer-123").include_deleted()
            ```

        Note:
            Mutually exclusive with only_deleted().
        """
        self._include_deleted = True
        self._only_deleted = False
        return self

    def only_deleted(self) -> "FluentSpecificationBuilder[T]":
        """Only return soft-deleted records.

        Returns only records where deleted_at IS NOT NULL.

        Returns:
            Self for chaining

        Example:
            ```python
            # Find deleted orders for a customer
            builder.equals("customer_id", "customer-123").only_deleted()
            ```

        Note:
            Mutually exclusive with include_deleted().
        """
        self._only_deleted = True
        self._include_deleted = False
        return self

    # ============================================================================
    # Ordering
    # ============================================================================

    def order_by(self, field: str, descending: bool = False) -> "FluentSpecificationBuilder[T]":
        """Add ordering by field.

        Args:
            field: Field name to sort by
            descending: If True, sort descending (default: ascending)

        Returns:
            Self for chaining

        Example:
            ```python
            builder.order_by("created_at")                  # Ascending
            builder.order_by("total_amount", descending=True)  # Descending

            # Multiple orderings
            builder.order_by("status").order_by("created_at", descending=True)
            ```

        Note:
            Multiple order_by calls are cumulative (first takes precedence).
        """
        from bento.persistence.specification.core.types import SortDirection

        direction = SortDirection.DESC if descending else SortDirection.ASC
        self._sorts.append(Sort(field=field, direction=direction))
        return self

    # ============================================================================
    # Pagination
    # ============================================================================

    def paginate(self, page: int, size: int) -> "FluentSpecificationBuilder[T]":
        """Set pagination using page/size style.

        Args:
            page: Page number starting from 1
            size: Page size (items per page)

        Returns:
            Self for chaining

        Example:
            ```python
            builder.paginate(page=2, size=20)
            ```

        Note:
            Internally this is converted to limit/offset in build():
            - limit = size
            - offset = (page - 1) * size
        """
        if page < 1:
            raise ValueError("page must be >= 1")
        if size < 1:
            raise ValueError("size must be >= 1")

        self._limit_value = size
        self._offset_value = (page - 1) * size
        return self

    def limit(self, count: int) -> "FluentSpecificationBuilder[T]":
        """Limit number of results.

        Args:
            count: Maximum number of records to return

        Returns:
            Self for chaining

        Example:
            ```python
            builder.limit(10)  # Top 10 records
            ```

        Note:
            Combine with offset() for pagination.
        """
        self._limit_value = count
        return self

    def offset(self, count: int) -> "FluentSpecificationBuilder[T]":
        """Skip first N results.

        Args:
            count: Number of records to skip

        Returns:
            Self for chaining

        Example:
            ```python
            # Pagination: Page 3, 10 per page
            builder.limit(10).offset(20)
            ```

        Note:
            Typically used with limit() for pagination.
        """
        self._offset_value = count
        return self

    # ============================================================================
    # Build
    # ============================================================================

    def build(self) -> CompositeSpecification:
        """Build the final Specification object.

        Returns:
            Specification object that can be used with repositories

        Example:
            ```python
            spec = builder.equals("status", "pending").build()
            orders = await repo.find_many(spec)
            ```

        Note:
            - Automatically adds deleted_at IS NULL unless include_deleted() called
            - If only_deleted() called, adds deleted_at IS NOT NULL
        """
        # Start with base specification
        filters = self._filters.copy()

        # Handle soft-delete logic
        if self._only_deleted:
            # Only deleted records (deleted_at IS NOT NULL)
            filters.append(
                Filter(field="deleted_at", operator=FilterOperator.IS_NOT_NULL, value=None)
            )
        elif not self._include_deleted:
            # Default: exclude deleted (deleted_at IS NULL)
            filters.append(Filter(field="deleted_at", operator=FilterOperator.IS_NULL, value=None))
        # If include_deleted=True, don't add any deleted_at filter

        # Pagination: convert limit/offset → PageParams
        page_params: PageParams | None = None
        if self._limit_value is not None or self._offset_value is not None:
            size = self._limit_value if self._limit_value is not None else 10
            off = self._offset_value if self._offset_value is not None else 0
            page_num = (off // size) + 1 if size > 0 else 1
            page_params = PageParams(page=page_num, size=size)

        # Create CompositeSpecification
        spec = CompositeSpecification(
            filters=filters,
            sorts=self._sorts.copy(),
            page=page_params,
        )

        return spec

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"FluentSpecificationBuilder({self._entity_type.__name__}): "
            f"{len(self._filters)} filters, "
            f"{len(self._sorts)} orderings, "
            f"limit={self._limit_value}, offset={self._offset_value}"
        )
