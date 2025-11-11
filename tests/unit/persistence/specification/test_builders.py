"""Unit tests for Specification builders."""

from datetime import date, datetime

from bento.persistence.specification import (
    AggregateSpecificationBuilder,
    CompositeSpecification,
    EntitySpecificationBuilder,
    FilterOperator,
    SortDirection,
    SpecificationBuilder,
)


class TestSpecificationBuilder:
    """Tests for base SpecificationBuilder."""

    def test_create_empty_builder(self):
        """Test creating an empty builder."""
        builder = SpecificationBuilder()
        spec = builder.build()

        assert isinstance(spec, CompositeSpecification)
        assert len(spec.filters) == 0
        assert len(spec.sorts) == 0
        assert spec.page is None

    def test_add_filter(self):
        """Test adding a single filter."""
        builder = SpecificationBuilder()
        builder.where("status", "=", "active")
        spec = builder.build()

        assert len(spec.filters) == 1
        assert spec.filters[0].field == "status"
        assert spec.filters[0].operator == FilterOperator.EQUALS
        assert spec.filters[0].value == "active"

    def test_add_multiple_filters(self):
        """Test adding multiple filters."""
        builder = SpecificationBuilder()
        builder.where("status", "=", "active")
        builder.where("age", ">=", 18)
        spec = builder.build()

        assert len(spec.filters) == 2
        assert spec.filters[0].field == "status"
        assert spec.filters[1].field == "age"

    def test_fluent_interface(self):
        """Test fluent interface returns self."""
        builder = SpecificationBuilder()
        result = builder.where("status", "=", "active")
        assert result is builder

    def test_order_by_asc(self):
        """Test adding ascending sort."""
        builder = SpecificationBuilder()
        builder.order_by("created_at", "asc")
        spec = builder.build()

        assert len(spec.sorts) == 1
        assert spec.sorts[0].field == "created_at"
        assert spec.sorts[0].direction == SortDirection.ASC

    def test_order_by_desc(self):
        """Test adding descending sort."""
        builder = SpecificationBuilder()
        builder.order_by("created_at", "desc")
        spec = builder.build()

        assert len(spec.sorts) == 1
        assert spec.sorts[0].direction == SortDirection.DESC

    def test_multiple_sorts(self):
        """Test adding multiple sorts."""
        builder = SpecificationBuilder()
        builder.order_by("priority", "desc")
        builder.order_by("created_at", "asc")
        spec = builder.build()

        assert len(spec.sorts) == 2
        assert spec.sorts[0].field == "priority"
        assert spec.sorts[1].field == "created_at"

    def test_paginate(self):
        """Test adding pagination."""
        builder = SpecificationBuilder()
        builder.paginate(page=2, size=20)
        spec = builder.build()

        assert spec.page is not None
        assert spec.page.page == 2
        assert spec.page.size == 20

    def test_complex_specification(self):
        """Test building complex specification with all features."""
        builder = SpecificationBuilder()
        spec = (
            builder.where("status", "=", "active")
            .where("age", ">=", 18)
            .order_by("created_at", "desc")
            .order_by("name", "asc")
            .paginate(page=1, size=10)
            .build()
        )

        assert len(spec.filters) == 2
        assert len(spec.sorts) == 2
        assert spec.page is not None
        assert spec.page.page == 1
        assert spec.page.size == 10

    def test_build_multiple_times(self):
        """Test that building multiple times creates independent specs."""
        builder = SpecificationBuilder()
        builder.where("status", "=", "active")

        spec1 = builder.build()
        builder.where("age", ">=", 18)
        spec2 = builder.build()

        # spec1 should only have status filter
        assert len(spec1.filters) == 1
        # spec2 should have both filters
        assert len(spec2.filters) == 2


class TestEntitySpecificationBuilder:
    """Tests for EntitySpecificationBuilder."""

    def test_by_id(self):
        """Test filtering by ID."""
        builder = EntitySpecificationBuilder()
        spec = builder.include_deleted().by_id("123").build()

        assert len(spec.filters) == 1
        assert spec.filters[0].field == "id"
        assert spec.filters[0].value == "123"

    def test_by_status(self):
        """Test filtering by status."""
        builder = EntitySpecificationBuilder()
        spec = builder.include_deleted().by_status("active").build()

        assert len(spec.filters) == 1
        assert spec.filters[0].field == "status"
        assert spec.filters[0].value == "active"

    def test_is_active_default(self):
        """Test is_active filter with default True."""
        builder = EntitySpecificationBuilder()
        spec = builder.include_deleted().is_active().build()

        assert len(spec.filters) == 1
        assert spec.filters[0].field == "is_active"
        assert spec.filters[0].value is True

    def test_is_active_false(self):
        """Test is_active filter with False."""
        builder = EntitySpecificationBuilder()
        spec = builder.include_deleted().is_active(False).build()

        assert len(spec.filters) == 1
        assert spec.filters[0].value is False

    def test_default_excludes_deleted(self):
        """Test that EntitySpecificationBuilder excludes soft-deleted records by default."""
        builder = EntitySpecificationBuilder()
        spec = builder.build()

        # Should have default deleted_at IS NULL filter
        assert len(spec.filters) == 1
        assert spec.filters[0].field == "deleted_at"
        assert spec.filters[0].operator == FilterOperator.IS_NULL

    def test_include_deleted(self):
        """Test include_deleted removes the default soft delete filter."""
        builder = EntitySpecificationBuilder()
        spec = builder.include_deleted().build()

        # Should have NO filters after removing default
        assert len(spec.filters) == 0

    def test_only_deleted(self):
        """Test only_deleted queries only soft-deleted records."""
        builder = EntitySpecificationBuilder()
        spec = builder.include_deleted().only_deleted().build()

        # Should use deleted_at IS NOT NULL
        assert len(spec.filters) == 1
        assert spec.filters[0].field == "deleted_at"
        assert spec.filters[0].operator == FilterOperator.IS_NOT_NULL

    def test_created_after(self):
        """Test created_after filter."""
        after_date = datetime(2024, 1, 1)
        builder = EntitySpecificationBuilder()
        spec = builder.include_deleted().created_after(after_date).build()

        assert len(spec.filters) == 1
        assert spec.filters[0].field == "created_at"

    def test_created_before(self):
        """Test created_before filter."""
        before_date = datetime(2024, 12, 31)
        builder = EntitySpecificationBuilder()
        spec = builder.include_deleted().created_before(before_date).build()

        assert len(spec.filters) == 1
        assert spec.filters[0].field == "created_at"

    def test_created_in_last_days(self):
        """Test created_in_last_days filter."""
        builder = EntitySpecificationBuilder()
        spec = builder.include_deleted().created_in_last_days(30).build()

        assert len(spec.filters) == 1
        assert spec.filters[0].field == "created_at"

    def test_created_in_month(self):
        """Test created_in_month filter."""
        builder = EntitySpecificationBuilder()
        spec = builder.include_deleted().created_in_month(2024, 11).build()

        assert len(spec.filters) == 1
        assert spec.filters[0].field == "created_at"

    def test_updated_after(self):
        """Test updated_after filter."""
        after_date = datetime(2024, 1, 1)
        builder = EntitySpecificationBuilder()
        spec = builder.include_deleted().updated_after(after_date).build()

        assert len(spec.filters) == 1
        assert spec.filters[0].field == "updated_at"

    def test_updated_in_last_days(self):
        """Test updated_in_last_days filter."""
        builder = EntitySpecificationBuilder()
        spec = builder.include_deleted().updated_in_last_days(7).build()

        assert len(spec.filters) == 1
        assert spec.filters[0].field == "updated_at"

    def test_by_tenant(self):
        """Test by_tenant filter."""
        builder = EntitySpecificationBuilder()
        spec = builder.include_deleted().by_tenant("tenant_123").build()

        assert len(spec.filters) == 1
        assert spec.filters[0].field == "tenant_id"
        assert spec.filters[0].value == "tenant_123"

    def test_by_created_by(self):
        """Test by_created_by filter."""
        builder = EntitySpecificationBuilder()
        spec = builder.include_deleted().by_created_by("user_123").build()

        assert len(spec.filters) == 1
        assert spec.filters[0].field == "created_by"
        assert spec.filters[0].value == "user_123"

    def test_by_updated_by(self):
        """Test by_updated_by filter."""
        builder = EntitySpecificationBuilder()
        spec = builder.include_deleted().by_updated_by("user_456").build()

        assert len(spec.filters) == 1
        assert spec.filters[0].field == "updated_by"
        assert spec.filters[0].value == "user_456"

    def test_complex_entity_query(self):
        """Test building complex entity query."""
        spec = (
            EntitySpecificationBuilder()
            .is_active()
            # .not_deleted() - Not needed: default behavior excludes soft-deleted
            .created_in_last_days(30)
            .by_tenant("tenant_123")
            .order_by("created_at", "desc")
            .paginate(page=1, size=20)
            .build()
        )

        # With default soft delete filter: deleted_at IS NULL
        assert len(spec.filters) == 4
        assert spec.filters[0].field == "deleted_at"  # Default filter
        assert spec.filters[1].field == "is_active"
        assert spec.filters[2].field == "created_at"
        assert spec.filters[3].field == "tenant_id"
        assert len(spec.sorts) == 1
        assert spec.page is not None
        assert spec.page.size == 20


class TestAggregateSpecificationBuilder:
    """Tests for AggregateSpecificationBuilder."""

    def test_with_version(self):
        """Test filtering by exact version."""
        builder = AggregateSpecificationBuilder()
        spec = builder.with_version(5).build()

        assert len(spec.filters) == 1
        assert spec.filters[0].field == "version"
        assert spec.filters[0].value == 5

    def test_with_minimum_version(self):
        """Test filtering by minimum version."""
        builder = AggregateSpecificationBuilder()
        spec = builder.with_minimum_version(3).build()

        assert len(spec.filters) == 1
        assert spec.filters[0].field == "version"
        assert spec.filters[0].operator == FilterOperator.GREATER_EQUAL

    def test_with_maximum_version(self):
        """Test filtering by maximum version."""
        builder = AggregateSpecificationBuilder()
        spec = builder.with_maximum_version(10).build()

        assert len(spec.filters) == 1
        assert spec.filters[0].field == "version"
        assert spec.filters[0].operator == FilterOperator.LESS_EQUAL

    def test_with_version_range(self):
        """Test filtering by version range."""
        builder = AggregateSpecificationBuilder()
        spec = builder.with_version_range(1, 10).build()

        assert len(spec.filters) == 1
        assert spec.filters[0].field == "version"
        assert spec.filters[0].operator == FilterOperator.BETWEEN

    def test_by_aggregate_id(self):
        """Test filtering by aggregate ID."""
        builder = AggregateSpecificationBuilder()
        spec = builder.by_aggregate_id("agg_123").build()

        assert len(spec.filters) == 1
        assert spec.filters[0].field == "id"
        assert spec.filters[0].value == "agg_123"

    def test_by_aggregate_type(self):
        """Test filtering by aggregate type."""
        builder = AggregateSpecificationBuilder()
        spec = builder.by_aggregate_type("Order").build()

        assert len(spec.filters) == 1
        assert spec.filters[0].field == "aggregate_type"
        assert spec.filters[0].value == "Order"

    def test_complex_aggregate_query(self):
        """Test building complex aggregate query."""
        spec = (
            AggregateSpecificationBuilder()
            .with_minimum_version(1)
            .updated_in_last_days(30)
            .is_active()
            .order_by("updated_at", "desc")
            .paginate(page=1, size=10)
            .build()
        )

        assert len(spec.filters) == 3
        assert spec.filters[0].field == "version"
        assert spec.filters[1].field == "updated_at"
        assert spec.filters[2].field == "is_active"
        assert len(spec.sorts) == 1
        assert spec.page is not None
        assert spec.page.size == 10


class TestBuilderInheritance:
    """Tests for builder inheritance and composition."""

    def test_aggregate_inherits_entity_methods(self):
        """Test that AggregateSpecificationBuilder inherits EntitySpecificationBuilder methods."""
        spec = (
            AggregateSpecificationBuilder()
            .is_active()  # From EntitySpecificationBuilder
            .with_version(5)  # From AggregateSpecificationBuilder
            .build()
        )

        assert len(spec.filters) == 2
        assert spec.filters[0].field == "is_active"
        assert spec.filters[1].field == "version"

    def test_entity_inherits_base_methods(self):
        """Test that EntitySpecificationBuilder inherits SpecificationBuilder methods."""
        spec = (
            EntitySpecificationBuilder()
            .where("custom_field", "=", "value")  # From base
            .is_active()  # From EntitySpecificationBuilder
            .build()
        )

        # EntitySpecificationBuilder has default deleted_at IS NULL filter
        assert len(spec.filters) == 3
        assert spec.filters[0].field == "deleted_at"  # Default filter
        assert spec.filters[1].field == "custom_field"
        assert spec.filters[2].field == "is_active"


class TestBuilderEdgeCases:
    """Tests for builder edge cases."""

    def test_paginate_without_filters(self):
        """Test pagination without any filters."""
        spec = SpecificationBuilder().paginate(page=1, size=10).build()

        assert len(spec.filters) == 0
        assert spec.page is not None

    def test_sort_without_filters(self):
        """Test sorting without any filters."""
        spec = SpecificationBuilder().order_by("name", "asc").build()

        assert len(spec.filters) == 0
        assert len(spec.sorts) == 1

    def test_overwrite_pagination(self):
        """Test that pagination can be overwritten."""
        builder = SpecificationBuilder()
        builder.paginate(page=1, size=10)
        builder.paginate(page=2, size=20)
        spec = builder.build()

        # Last pagination should win
        assert spec.page is not None
        assert spec.page.page == 2
        assert spec.page.size == 20

    def test_created_between_with_date_objects(self):
        """Test created_between with date objects (not datetime)."""
        start = date(2024, 1, 1)
        end = date(2024, 12, 31)
        spec = EntitySpecificationBuilder().created_between(start, end).build()

        # EntitySpecificationBuilder has default deleted_at IS NULL filter
        assert len(spec.filters) == 2
        assert spec.filters[0].field == "deleted_at"  # Default filter
        assert spec.filters[1].field == "created_at"
