"""Unit tests for Specification core types."""

import pytest

from bento.persistence.specification.core.types import (
    Filter,
    FilterGroup,
    FilterOperator,
    Having,
    LogicalOperator,
    Page,
    PageParams,
    Sort,
    SortDirection,
    Statistic,
    StatisticalFunction,
)


class TestFilterOperator:
    """Tests for FilterOperator enum."""

    def test_all_operators_defined(self):
        """Test that all expected operators are defined."""
        assert FilterOperator.EQUALS == "eq"
        assert FilterOperator.NOT_EQUALS == "ne"
        assert FilterOperator.GREATER_THAN == "gt"
        assert FilterOperator.IN == "in"
        assert FilterOperator.LIKE == "like"
        assert FilterOperator.ARRAY_CONTAINS == "array_contains"
        assert FilterOperator.JSON_CONTAINS == "json_contains"


class TestFilter:
    """Tests for Filter dataclass."""

    def test_create_simple_filter(self):
        """Test creating a basic filter."""
        f = Filter(field="status", operator=FilterOperator.EQUALS, value="active")
        assert f.field == "status"
        assert f.operator == FilterOperator.EQUALS
        assert f.value == "active"

    def test_filter_with_string_operator(self):
        """Test creating filter with string operator (auto-convert)."""
        f = Filter(field="age", operator=FilterOperator.GREATER_THAN, value=18)
        assert f.operator == FilterOperator.GREATER_THAN

    def test_filter_empty_field_raises(self):
        """Test that empty field raises ValueError."""
        with pytest.raises(ValueError, match="field cannot be empty"):
            Filter(field="", operator=FilterOperator.EQUALS, value="test")

    def test_filter_invalid_operator_raises(self):
        """Test that invalid operator raises ValueError."""
        with pytest.raises(ValueError, match="Invalid operator"):
            Filter(field="name", operator="invalid", value="test")  # type: ignore[arg-type]

    def test_in_operator_requires_iterable(self):
        """Test that IN operator requires iterable value."""
        # Valid
        f = Filter(field="status", operator=FilterOperator.IN, value=["a", "b"])
        assert f.value == ["a", "b"]

        # Invalid - string is iterable but not allowed
        with pytest.raises(ValueError, match="must be iterable"):
            Filter(field="status", operator=FilterOperator.IN, value="abc")

    def test_like_operator_requires_string(self):
        """Test that LIKE operator requires string value."""
        # Valid
        f = Filter(field="name", operator=FilterOperator.LIKE, value="%test%")
        assert f.value == "%test%"

        # Invalid
        with pytest.raises(ValueError, match="must be string"):
            Filter(field="name", operator=FilterOperator.LIKE, value=123)

    def test_between_operator_validation(self):
        """Test BETWEEN operator validation."""
        # Valid
        f = Filter(
            field="age",
            operator=FilterOperator.BETWEEN,
            value={"start": 18, "end": 65},
        )
        assert f.value == {"start": 18, "end": 65}

        # Missing keys
        with pytest.raises(ValueError, match="must be a dict with 'start' and 'end'"):
            Filter(field="age", operator=FilterOperator.BETWEEN, value={"start": 18})

        # Start > end
        with pytest.raises(ValueError, match="Start value must be less than"):
            Filter(
                field="age",
                operator=FilterOperator.BETWEEN,
                value={"start": 65, "end": 18},
            )

    def test_array_empty_no_value_needed(self):
        """Test that array empty operators don't need value."""
        # Valid
        f = Filter(field="tags", operator=FilterOperator.ARRAY_EMPTY, value=None)
        assert f.value is None

        # Invalid - value provided
        with pytest.raises(ValueError, match="does not accept a value"):
            Filter(field="tags", operator=FilterOperator.ARRAY_EMPTY, value=True)

    def test_json_operators_validation(self):
        """Test JSON operators validation."""
        # Valid JSON_CONTAINS
        f = Filter(
            field="data",
            operator=FilterOperator.JSON_CONTAINS,
            value={"key": "value"},
        )
        assert f.value == {"key": "value"}

        # Invalid JSON_CONTAINS (not dict/list)
        with pytest.raises(ValueError, match="must be a dict or list"):
            Filter(field="data", operator=FilterOperator.JSON_CONTAINS, value="string")

        # Valid JSON_HAS_KEY
        f = Filter(field="data", operator=FilterOperator.JSON_HAS_KEY, value="key")
        assert f.value == "key"

        # Invalid JSON_HAS_KEY (not string)
        with pytest.raises(ValueError, match="must be a string"):
            Filter(field="data", operator=FilterOperator.JSON_HAS_KEY, value=123)


class TestSort:
    """Tests for Sort dataclass."""

    def test_create_simple_sort(self):
        """Test creating a basic sort."""
        s = Sort(field="created_at", direction=SortDirection.DESC)
        assert s.field == "created_at"
        assert s.direction == SortDirection.DESC

    def test_sort_default_direction(self):
        """Test that default direction is ASC."""
        s = Sort(field="name")
        assert s.direction == SortDirection.ASC

    def test_sort_with_string_direction(self):
        """Test creating sort with string direction (auto-convert)."""
        s = Sort(field="age", direction=SortDirection.DESC)
        assert s.direction == SortDirection.DESC

    def test_sort_empty_field_raises(self):
        """Test that empty field raises ValueError."""
        with pytest.raises(ValueError, match="field cannot be empty"):
            Sort(field="", direction=SortDirection.ASC)

    def test_sort_invalid_direction_raises(self):
        """Test that invalid direction raises ValueError."""
        with pytest.raises(ValueError, match="Invalid sort direction"):
            Sort(field="name", direction="invalid")  # type: ignore[arg-type]

    def test_sort_ascending_property(self):
        """Test ascending property for backward compatibility."""
        s_asc = Sort(field="name", direction=SortDirection.ASC)
        s_desc = Sort(field="name", direction=SortDirection.DESC)

        assert s_asc.ascending is True
        assert s_desc.ascending is False


class TestPageParams:
    """Tests for PageParams dataclass."""

    def test_create_page_params(self):
        """Test creating page params."""
        p = PageParams(page=2, size=20)
        assert p.page == 2
        assert p.size == 20

    def test_default_page_params(self):
        """Test default page params."""
        p = PageParams()
        assert p.page == 1
        assert p.size == 10

    def test_page_params_offset_calculation(self):
        """Test offset calculation."""
        p1 = PageParams(page=1, size=10)
        assert p1.offset == 0

        p2 = PageParams(page=2, size=10)
        assert p2.offset == 10

        p3 = PageParams(page=5, size=20)
        assert p3.offset == 80

    def test_page_params_limit_property(self):
        """Test limit property (alias for size)."""
        p = PageParams(page=1, size=25)
        assert p.limit == 25

    def test_page_params_validation(self):
        """Test page params validation."""
        # Invalid page
        with pytest.raises(ValueError, match="Page must be >= 1"):
            PageParams(page=0, size=10)

        # Invalid size
        with pytest.raises(ValueError, match="Size must be >= 1"):
            PageParams(page=1, size=0)


class TestPage:
    """Tests for Page generic container."""

    def test_create_page_manually(self):
        """Test creating page manually."""
        items = [1, 2, 3, 4, 5]
        page = Page(
            items=items,
            total=50,
            page=1,
            size=5,
            total_pages=10,
            has_next=True,
            has_prev=False,
        )
        assert page.items == items
        assert page.total == 50
        assert page.page == 1
        assert page.has_next is True
        assert page.has_prev is False

    def test_create_page_with_factory(self):
        """Test creating page with factory method."""
        items = [1, 2, 3, 4, 5]
        page = Page.create(items=items, total=50, page=1, size=5)

        assert page.items == items
        assert page.total == 50
        assert page.page == 1
        assert page.size == 5
        assert page.total_pages == 10
        assert page.has_next is True
        assert page.has_prev is False

    def test_page_metadata_calculations(self):
        """Test page metadata calculations."""
        # First page
        p1 = Page.create(items=[1, 2], total=10, page=1, size=2)
        assert p1.total_pages == 5
        assert p1.has_next is True
        assert p1.has_prev is False

        # Middle page
        p2 = Page.create(items=[5, 6], total=10, page=3, size=2)
        assert p2.has_next is True
        assert p2.has_prev is True

        # Last page
        p3 = Page.create(items=[9, 10], total=10, page=5, size=2)
        assert p3.has_next is False
        assert p3.has_prev is True

    def test_page_empty_results(self):
        """Test page with empty results."""
        page = Page.create(items=[], total=0, page=1, size=10)
        assert page.items == []
        assert page.total == 0
        assert page.total_pages == 0  # No pages when no results
        assert page.has_next is False
        assert page.has_prev is False


class TestFilterGroup:
    """Tests for FilterGroup dataclass."""

    def test_create_filter_group(self):
        """Test creating a filter group."""
        filters = (
            Filter(field="status", operator=FilterOperator.EQUALS, value="active"),
            Filter(field="age", operator=FilterOperator.GREATER_EQUAL, value=18),
        )
        group = FilterGroup(filters=filters, operator=LogicalOperator.AND)

        assert len(group.filters) == 2
        assert group.operator == LogicalOperator.AND

    def test_filter_group_default_operator(self):
        """Test that default operator is AND."""
        filters = (Filter(field="status", operator=FilterOperator.EQUALS, value="active"),)
        group = FilterGroup(filters=filters)

        assert group.operator == LogicalOperator.AND

    def test_filter_group_with_string_operator(self):
        """Test creating filter group with string operator."""
        filters = (Filter(field="status", operator=FilterOperator.EQUALS, value="active"),)
        group = FilterGroup(filters=filters, operator="or")  # type: ignore[arg-type]

        assert group.operator == LogicalOperator.OR

    def test_filter_group_empty_raises(self):
        """Test that empty filter group raises ValueError."""
        with pytest.raises(ValueError, match="must contain at least one filter"):
            FilterGroup(filters=())

    def test_filter_group_invalid_operator_raises(self):
        """Test that invalid operator raises ValueError."""
        filters = (Filter(field="status", operator=FilterOperator.EQUALS, value="active"),)
        with pytest.raises(ValueError, match="Invalid logical operator"):
            FilterGroup(filters=filters, operator="invalid")  # type: ignore[arg-type]


class TestStatistic:
    """Tests for Statistic dataclass."""

    def test_create_statistic(self):
        """Test creating a statistic."""
        stat = Statistic(function=StatisticalFunction.COUNT, field="id", alias="total")
        assert stat.function == StatisticalFunction.COUNT
        assert stat.field == "id"
        assert stat.alias == "total"

    def test_statistic_with_string_function(self):
        """Test creating statistic with string function."""
        stat = Statistic(function="sum", field="amount")  # type: ignore[arg-type]
        assert stat.function == StatisticalFunction.SUM

    def test_statistic_empty_field_raises(self):
        """Test that empty field raises ValueError."""
        with pytest.raises(ValueError, match="Field cannot be empty"):
            Statistic(function=StatisticalFunction.COUNT, field="")

    def test_statistic_invalid_function_raises(self):
        """Test that invalid function raises ValueError."""
        with pytest.raises(ValueError, match="Invalid statistical function"):
            Statistic(function="invalid", field="id")  # type: ignore[arg-type]

    def test_statistic_distinct_flag(self):
        """Test distinct flag."""
        stat = Statistic(function=StatisticalFunction.COUNT, field="user_id", distinct=True)
        assert stat.distinct is True

    def test_group_concat_separator(self):
        """Test GROUP_CONCAT with separator."""
        stat = Statistic(function=StatisticalFunction.GROUP_CONCAT, field="tags", separator="; ")
        assert stat.separator == "; "

    def test_group_concat_default_separator(self):
        """Test GROUP_CONCAT default separator."""
        stat = Statistic(function=StatisticalFunction.GROUP_CONCAT, field="tags")
        assert stat.separator == ","

    def test_separator_only_for_group_concat(self):
        """Test that separator is only valid for GROUP_CONCAT."""
        with pytest.raises(ValueError, match="only valid for GROUP_CONCAT"):
            Statistic(function=StatisticalFunction.SUM, field="amount", separator=",")


class TestHaving:
    """Tests for Having dataclass."""

    def test_create_having(self):
        """Test creating a having condition."""
        having = Having(
            field="total",
            operator=FilterOperator.GREATER_THAN,
            value=100,
        )
        assert having.field == "total"
        assert having.operator == FilterOperator.GREATER_THAN
        assert having.value == 100

    def test_having_empty_field_raises(self):
        """Test that empty field raises ValueError."""
        with pytest.raises(ValueError, match="field cannot be empty"):
            Having(field="", operator=FilterOperator.EQUALS, value=0)

    def test_having_invalid_operator_raises(self):
        """Test that invalid operator raises ValueError."""
        with pytest.raises(ValueError, match="Invalid operator"):
            Having(field="total", operator="invalid", value=100)  # type: ignore[arg-type]
