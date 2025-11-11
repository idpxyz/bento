"""Unit tests for FluentSpecificationBuilder.

This test suite verifies that the FluentSpecificationBuilder correctly builds
Specification objects with the expected filters, ordering, and pagination.
"""

from bento.persistence.specification.builder.fluent import FluentSpecificationBuilder
from bento.persistence.specification.core import FilterOperator


# Test entity for specification building
class TestEntity:
    """Test entity class for fluent builder tests."""

    def __init__(self) -> None:
        """Initialize test entity."""
        self.id: str = ""
        self.name: str = ""
        self.status: str = ""
        self.amount: float = 0.0
        self.created_at: str = ""
        self.deleted_at: str | None = None


class TestFluentSpecificationBuilder:
    """Test suite for FluentSpecificationBuilder."""

    # ==========================================================================
    # Initialization Tests
    # ==========================================================================

    def test_initialization(self) -> None:
        """Test FluentBuilder initialization."""
        builder = FluentSpecificationBuilder(TestEntity)

        assert builder._entity_type == TestEntity
        assert builder._filters == []
        assert builder._sorts == []
        assert builder._limit_value is None
        assert builder._offset_value is None
        assert builder._include_deleted is False
        assert builder._only_deleted is False

    def test_repr(self) -> None:
        """Test string representation."""
        builder = FluentSpecificationBuilder(TestEntity)
        builder.equals("status", "active").limit(10)

        repr_str = repr(builder)
        assert "FluentSpecificationBuilder" in repr_str
        assert "TestEntity" in repr_str
        assert "1 filters" in repr_str

    # ==========================================================================
    # Comparison Operator Tests
    # ==========================================================================

    def test_equals(self) -> None:
        """Test equals filter."""
        builder = FluentSpecificationBuilder(TestEntity)
        result = builder.equals("status", "active")

        assert result is builder  # Returns self for chaining
        assert len(builder._filters) == 1
        assert builder._filters[0].field == "status"
        assert builder._filters[0].operator == FilterOperator.EQUALS
        assert builder._filters[0].value == "active"

    def test_not_equals(self) -> None:
        """Test not_equals filter."""
        builder = FluentSpecificationBuilder(TestEntity)
        builder.not_equals("status", "cancelled")

        assert len(builder._filters) == 1
        assert builder._filters[0].operator == FilterOperator.NOT_EQUALS
        assert builder._filters[0].value == "cancelled"

    def test_greater_than(self) -> None:
        """Test greater_than filter."""
        builder = FluentSpecificationBuilder(TestEntity)
        builder.greater_than("amount", 100)

        assert len(builder._filters) == 1
        assert builder._filters[0].field == "amount"
        assert builder._filters[0].operator == FilterOperator.GREATER_THAN
        assert builder._filters[0].value == 100

    def test_greater_than_or_equal(self) -> None:
        """Test greater_than_or_equal filter."""
        builder = FluentSpecificationBuilder(TestEntity)
        builder.greater_than_or_equal("amount", 100)

        assert len(builder._filters) == 1
        assert builder._filters[0].operator == FilterOperator.GREATER_EQUAL
        assert builder._filters[0].value == 100

    def test_less_than(self) -> None:
        """Test less_than filter."""
        builder = FluentSpecificationBuilder(TestEntity)
        builder.less_than("amount", 1000)

        assert len(builder._filters) == 1
        assert builder._filters[0].field == "amount"
        assert builder._filters[0].operator == FilterOperator.LESS_THAN
        assert builder._filters[0].value == 1000

    def test_less_than_or_equal(self) -> None:
        """Test less_than_or_equal filter."""
        builder = FluentSpecificationBuilder(TestEntity)
        builder.less_than_or_equal("amount", 1000)

        assert len(builder._filters) == 1
        assert builder._filters[0].operator == FilterOperator.LESS_EQUAL
        assert builder._filters[0].value == 1000

    def test_in(self) -> None:
        """Test IN filter."""
        builder = FluentSpecificationBuilder(TestEntity)
        builder.in_("status", ["pending", "processing"])

        assert len(builder._filters) == 1
        assert builder._filters[0].field == "status"
        assert builder._filters[0].operator == FilterOperator.IN
        assert builder._filters[0].value == ["pending", "processing"]

    def test_not_in(self) -> None:
        """Test NOT IN filter."""
        builder = FluentSpecificationBuilder(TestEntity)
        builder.not_in("status", ["cancelled", "failed"])

        assert len(builder._filters) == 1
        assert builder._filters[0].operator == FilterOperator.NOT_IN
        assert builder._filters[0].value == ["cancelled", "failed"]

    def test_like(self) -> None:
        """Test LIKE filter."""
        builder = FluentSpecificationBuilder(TestEntity)
        builder.like("name", "%laptop%")

        assert len(builder._filters) == 1
        assert builder._filters[0].field == "name"
        assert builder._filters[0].operator == FilterOperator.LIKE
        assert builder._filters[0].value == "%laptop%"

    def test_is_null(self) -> None:
        """Test IS NULL filter."""
        builder = FluentSpecificationBuilder(TestEntity)
        builder.is_null("deleted_at")

        assert len(builder._filters) == 1
        assert builder._filters[0].field == "deleted_at"
        assert builder._filters[0].operator == FilterOperator.IS_NULL
        assert builder._filters[0].value is None

    def test_is_not_null(self) -> None:
        """Test IS NOT NULL filter."""
        builder = FluentSpecificationBuilder(TestEntity)
        builder.is_not_null("deleted_at")

        assert len(builder._filters) == 1
        assert builder._filters[0].field == "deleted_at"
        assert builder._filters[0].operator == FilterOperator.IS_NOT_NULL
        assert builder._filters[0].value is None

    # ==========================================================================
    # Chaining Tests
    # ==========================================================================

    def test_multiple_filters_chaining(self) -> None:
        """Test chaining multiple filters."""
        builder = FluentSpecificationBuilder(TestEntity)
        result = (
            builder.equals("status", "active").greater_than("amount", 100).like("name", "%laptop%")
        )

        assert result is builder
        assert len(builder._filters) == 3
        assert builder._filters[0].field == "status"
        assert builder._filters[1].field == "amount"
        assert builder._filters[2].field == "name"

    def test_complex_query_chain(self) -> None:
        """Test complex chained query."""
        builder = (
            FluentSpecificationBuilder(TestEntity)
            .in_("status", ["pending", "processing"])
            .greater_than("amount", 50)
            .less_than("amount", 200)
            .like("name", "%product%")
            .order_by("created_at", descending=True)
            .limit(10)
            .offset(20)
        )

        assert len(builder._filters) == 4
        assert len(builder._sorts) == 1
        assert builder._limit_value == 10
        assert builder._offset_value == 20

    # ==========================================================================
    # Soft Delete Tests
    # ==========================================================================

    def test_include_deleted(self) -> None:
        """Test include_deleted flag."""
        builder = FluentSpecificationBuilder(TestEntity)
        result = builder.include_deleted()

        assert result is builder
        assert builder._include_deleted is True
        assert builder._only_deleted is False

    def test_only_deleted(self) -> None:
        """Test only_deleted flag."""
        builder = FluentSpecificationBuilder(TestEntity)
        result = builder.only_deleted()

        assert result is builder
        assert builder._only_deleted is True
        assert builder._include_deleted is False

    def test_only_deleted_overrides_include_deleted(self) -> None:
        """Test only_deleted overrides include_deleted."""
        builder = FluentSpecificationBuilder(TestEntity)
        builder.include_deleted().only_deleted()

        assert builder._only_deleted is True
        assert builder._include_deleted is False

    def test_include_deleted_overrides_only_deleted(self) -> None:
        """Test include_deleted overrides only_deleted."""
        builder = FluentSpecificationBuilder(TestEntity)
        builder.only_deleted().include_deleted()

        assert builder._include_deleted is True
        assert builder._only_deleted is False

    # ==========================================================================
    # Ordering Tests
    # ==========================================================================

    def test_order_by_ascending(self) -> None:
        """Test ascending order."""
        builder = FluentSpecificationBuilder(TestEntity)
        result = builder.order_by("created_at")

        assert result is builder
        assert len(builder._sorts) == 1
        assert builder._sorts[0].field == "created_at"
        from bento.persistence.specification.core.types import SortDirection

        assert builder._sorts[0].direction == SortDirection.ASC

    def test_order_by_descending(self) -> None:
        """Test descending order."""
        builder = FluentSpecificationBuilder(TestEntity)
        builder.order_by("amount", descending=True)

        from bento.persistence.specification.core.types import SortDirection

        assert len(builder._sorts) == 1
        assert builder._sorts[0].field == "amount"
        assert builder._sorts[0].direction == SortDirection.DESC

    def test_multiple_order_by(self) -> None:
        """Test multiple order by clauses."""
        builder = FluentSpecificationBuilder(TestEntity)
        builder.order_by("status").order_by("created_at", descending=True)

        from bento.persistence.specification.core.types import SortDirection

        assert len(builder._sorts) == 2
        assert builder._sorts[0].field == "status"
        assert builder._sorts[0].direction == SortDirection.ASC
        assert builder._sorts[1].field == "created_at"
        assert builder._sorts[1].direction == SortDirection.DESC

    # ==========================================================================
    # Pagination Tests
    # ==========================================================================

    def test_limit(self) -> None:
        """Test limit."""
        builder = FluentSpecificationBuilder(TestEntity)
        result = builder.limit(10)

        assert result is builder
        assert builder._limit_value == 10

    def test_offset(self) -> None:
        """Test offset."""
        builder = FluentSpecificationBuilder(TestEntity)
        result = builder.offset(20)

        assert result is builder
        assert builder._offset_value == 20

    def test_limit_and_offset(self) -> None:
        """Test limit and offset together (pagination)."""
        builder = FluentSpecificationBuilder(TestEntity)
        builder.limit(10).offset(20)

        assert builder._limit_value == 10
        assert builder._offset_value == 20

    def test_paginate(self) -> None:
        """Test paginate(page, size) maps to limit/offset and PageParams."""
        builder = FluentSpecificationBuilder(TestEntity)
        builder.paginate(page=2, size=20)

        # Internal state
        assert builder._limit_value == 20
        assert builder._offset_value == 20

        # Built specification should expose page/size and derived limit/offset
        spec = builder.build()
        assert spec.page is not None
        assert spec.page.page == 2
        assert spec.page.size == 20
        assert spec.limit == 20
        assert spec.offset == 20

    # ==========================================================================
    # Build Tests
    # ==========================================================================

    def test_build_simple(self) -> None:
        """Test building simple specification."""
        builder = FluentSpecificationBuilder(TestEntity)
        builder.equals("status", "active")

        spec = builder.build()

        # Should have 2 filters: status=active + deleted_at IS NULL (default)
        assert len(spec.filters) == 2
        assert spec.filters[0].field == "status"
        assert spec.filters[0].operator == FilterOperator.EQUALS
        assert spec.filters[1].field == "deleted_at"
        assert spec.filters[1].operator == FilterOperator.IS_NULL

    def test_build_with_include_deleted(self) -> None:
        """Test build with include_deleted (no deleted_at filter)."""
        builder = FluentSpecificationBuilder(TestEntity)
        builder.equals("status", "active").include_deleted()

        spec = builder.build()

        # Should have only 1 filter: status=active
        assert len(spec.filters) == 1
        assert spec.filters[0].field == "status"

    def test_build_with_only_deleted(self) -> None:
        """Test build with only_deleted (deleted_at IS NOT NULL)."""
        builder = FluentSpecificationBuilder(TestEntity)
        builder.equals("status", "active").only_deleted()

        spec = builder.build()

        # Should have 2 filters: status=active + deleted_at IS NOT NULL
        assert len(spec.filters) == 2
        assert spec.filters[0].field == "status"
        assert spec.filters[1].field == "deleted_at"
        assert spec.filters[1].operator == FilterOperator.IS_NOT_NULL

    def test_build_with_ordering(self) -> None:
        """Test build with ordering."""
        builder = FluentSpecificationBuilder(TestEntity)
        builder.order_by("created_at", descending=True)

        spec = builder.build()

        from bento.persistence.specification.core.types import SortDirection

        assert len(spec.sorts) == 1
        assert spec.sorts[0].field == "created_at"
        assert spec.sorts[0].direction == SortDirection.DESC

    def test_build_with_pagination(self) -> None:
        """Test build with pagination."""
        builder = FluentSpecificationBuilder(TestEntity)
        builder.limit(10).offset(20)

        spec = builder.build()

        assert spec.limit == 10
        assert spec.offset == 20

    def test_build_complex_specification(self) -> None:
        """Test building complex specification."""
        builder = (
            FluentSpecificationBuilder(TestEntity)
            .in_("status", ["pending", "processing"])
            .greater_than("amount", 100)
            .less_than("amount", 500)
            .like("name", "%product%")
            .order_by("amount")
            .order_by("created_at", descending=True)
            .limit(50)
            .offset(100)
        )

        spec = builder.build()

        # 4 custom filters + 1 deleted_at filter = 5 total
        assert len(spec.filters) == 5
        assert len(spec.sorts) == 2
        assert spec.limit == 50
        assert spec.offset == 100

    def test_build_is_idempotent(self) -> None:
        """Test that build() can be called multiple times."""
        builder = FluentSpecificationBuilder(TestEntity)
        builder.equals("status", "active")

        spec1 = builder.build()
        spec2 = builder.build()

        # Both specs should have the same content
        assert len(spec1.filters) == len(spec2.filters)
        assert spec1.filters[0].field == spec2.filters[0].field

    # ==========================================================================
    # Edge Cases
    # ==========================================================================

    def test_empty_builder(self) -> None:
        """Test building with no filters (only default soft-delete)."""
        builder = FluentSpecificationBuilder(TestEntity)
        spec = builder.build()

        # Should only have deleted_at IS NULL filter
        assert len(spec.filters) == 1
        assert spec.filters[0].field == "deleted_at"
        assert spec.filters[0].operator == FilterOperator.IS_NULL

    def test_empty_builder_with_include_deleted(self) -> None:
        """Test building with no filters and include_deleted."""
        builder = FluentSpecificationBuilder(TestEntity)
        builder.include_deleted()

        spec = builder.build()

        # Should have no filters at all
        assert len(spec.filters) == 0

    def test_chainable_return_values(self) -> None:
        """Test all methods return self for chaining."""
        builder = FluentSpecificationBuilder(TestEntity)

        assert builder.equals("id", "1") is builder
        assert builder.not_equals("status", "cancelled") is builder
        assert builder.greater_than("amount", 0) is builder
        assert builder.less_than("amount", 1000) is builder
        assert builder.in_("status", ["a", "b"]) is builder
        assert builder.like("name", "%test%") is builder
        assert builder.is_null("deleted_at") is builder
        assert builder.order_by("created_at") is builder
        assert builder.limit(10) is builder
        assert builder.offset(0) is builder
        assert builder.include_deleted() is builder
