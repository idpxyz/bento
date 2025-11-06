"""Unit tests for Specification criteria."""

from datetime import date, datetime, timedelta

from bento.persistence.specification.core.types import Filter, FilterOperator
from bento.persistence.specification.criteria import (
    AfterCriterion,
    And,
    ArrayContainsCriterion,
    ArrayEmptyCriterion,
    ArrayOverlapsCriterion,
    BeforeCriterion,
    BetweenCriterion,
    ContainsCriterion,
    DateEqualsCriterion,
    DateRangeCriterion,
    EndsWithCriterion,
    EqualsCriterion,
    GreaterEqualCriterion,
    GreaterThanCriterion,
    IContainsCriterion,
    ILikeCriterion,
    InCriterion,
    IsNotNullCriterion,
    IsNullCriterion,
    JsonContainsCriterion,
    JsonExistsCriterion,
    JsonHasKeyCriterion,
    LastNDaysCriterion,
    LastNHoursCriterion,
    LessEqualCriterion,
    LessThanCriterion,
    LikeCriterion,
    NotEqualsCriterion,
    NotInCriterion,
    OnOrAfterCriterion,
    OnOrBeforeCriterion,
    Or,
    RegexCriterion,
    StartsWithCriterion,
    ThisMonthCriterion,
    ThisWeekCriterion,
    ThisYearCriterion,
    TodayCriterion,
    YesterdayCriterion,
)


class TestComparisonCriteria:
    """Tests for comparison criteria."""

    def test_equals_criterion(self):
        """Test EqualsCriterion."""
        criterion = EqualsCriterion("status", "active")
        filter = criterion.to_filter()

        assert isinstance(filter, Filter)
        assert filter.field == "status"
        assert filter.operator == FilterOperator.EQUALS
        assert filter.value == "active"

    def test_not_equals_criterion(self):
        """Test NotEqualsCriterion."""
        criterion = NotEqualsCriterion("status", "deleted")
        filter = criterion.to_filter()

        assert filter.operator == FilterOperator.NOT_EQUALS
        assert filter.value == "deleted"

    def test_greater_than_criterion(self):
        """Test GreaterThanCriterion."""
        criterion = GreaterThanCriterion("age", 18)
        filter = criterion.to_filter()

        assert filter.operator == FilterOperator.GREATER_THAN
        assert filter.value == 18

    def test_greater_equal_criterion(self):
        """Test GreaterEqualCriterion."""
        criterion = GreaterEqualCriterion("age", 18)
        filter = criterion.to_filter()

        assert filter.operator == FilterOperator.GREATER_EQUAL
        assert filter.value == 18

    def test_less_than_criterion(self):
        """Test LessThanCriterion."""
        criterion = LessThanCriterion("age", 65)
        filter = criterion.to_filter()

        assert filter.operator == FilterOperator.LESS_THAN
        assert filter.value == 65

    def test_less_equal_criterion(self):
        """Test LessEqualCriterion."""
        criterion = LessEqualCriterion("age", 65)
        filter = criterion.to_filter()

        assert filter.operator == FilterOperator.LESS_EQUAL
        assert filter.value == 65

    def test_between_criterion(self):
        """Test BetweenCriterion."""
        criterion = BetweenCriterion("age", 18, 65)
        filter = criterion.to_filter()

        assert filter.operator == FilterOperator.BETWEEN
        assert filter.value == {"start": 18, "end": 65}

    def test_in_criterion(self):
        """Test InCriterion."""
        criterion = InCriterion("status", ["active", "pending"])
        filter = criterion.to_filter()

        assert filter.operator == FilterOperator.IN
        assert filter.value == ["active", "pending"]

    def test_not_in_criterion(self):
        """Test NotInCriterion."""
        criterion = NotInCriterion("status", ["deleted", "archived"])
        filter = criterion.to_filter()

        assert filter.operator == FilterOperator.NOT_IN
        assert filter.value == ["deleted", "archived"]

    def test_is_null_criterion(self):
        """Test IsNullCriterion."""
        criterion = IsNullCriterion("deleted_at")
        filter = criterion.to_filter()

        assert filter.operator == FilterOperator.IS_NULL
        assert filter.value is None

    def test_is_not_null_criterion(self):
        """Test IsNotNullCriterion."""
        criterion = IsNotNullCriterion("deleted_at")
        filter = criterion.to_filter()

        assert filter.operator == FilterOperator.IS_NOT_NULL
        assert filter.value is None


class TestTextCriteria:
    """Tests for text criteria."""

    def test_like_criterion(self):
        """Test LikeCriterion."""
        criterion = LikeCriterion("name", "%John%")
        filter = criterion.to_filter()

        assert filter.operator == FilterOperator.LIKE
        assert filter.value == "%John%"

    def test_ilike_criterion(self):
        """Test ILikeCriterion (case-insensitive)."""
        criterion = ILikeCriterion("name", "%john%")
        filter = criterion.to_filter()

        assert filter.operator == FilterOperator.ILIKE
        assert filter.value == "%john%"

    def test_contains_criterion(self):
        """Test ContainsCriterion."""
        criterion = ContainsCriterion("description", "important")
        filter = criterion.to_filter()

        # ContainsCriterion uses LIKE with % wildcards
        assert filter.operator == FilterOperator.LIKE
        assert filter.value == "%important%"

    def test_icontains_criterion(self):
        """Test IContainsCriterion (case-insensitive contains)."""
        criterion = IContainsCriterion("description", "IMPORTANT")
        filter = criterion.to_filter()

        # IContainsCriterion uses ILIKE with % wildcards
        assert filter.operator == FilterOperator.ILIKE
        assert filter.value == "%IMPORTANT%"

    def test_starts_with_criterion(self):
        """Test StartsWithCriterion."""
        criterion = StartsWithCriterion("name", "John")
        filter = criterion.to_filter()

        # StartsWithCriterion uses LIKE with trailing %
        assert filter.operator == FilterOperator.LIKE
        assert filter.value == "John%"

    def test_ends_with_criterion(self):
        """Test EndsWithCriterion."""
        criterion = EndsWithCriterion("email", "@example.com")
        filter = criterion.to_filter()

        # EndsWithCriterion uses LIKE with leading %
        assert filter.operator == FilterOperator.LIKE
        assert filter.value == "%@example.com"

    def test_regex_criterion(self):
        """Test RegexCriterion."""
        criterion = RegexCriterion("phone", r"^\d{3}-\d{4}$")
        filter = criterion.to_filter()

        assert filter.operator == FilterOperator.REGEX
        assert filter.value == r"^\d{3}-\d{4}$"


class TestArrayCriteria:
    """Tests for array criteria."""

    def test_array_contains_criterion(self):
        """Test ArrayContainsCriterion."""
        criterion = ArrayContainsCriterion("tags", ["python", "django"])
        filter = criterion.to_filter()

        assert filter.operator == FilterOperator.ARRAY_CONTAINS
        assert filter.value == ["python", "django"]

    def test_array_overlaps_criterion(self):
        """Test ArrayOverlapsCriterion."""
        criterion = ArrayOverlapsCriterion("tags", ["python", "ruby"])
        filter = criterion.to_filter()

        assert filter.operator == FilterOperator.ARRAY_OVERLAPS
        assert filter.value == ["python", "ruby"]

    def test_array_empty_criterion(self):
        """Test ArrayEmptyCriterion."""
        criterion = ArrayEmptyCriterion("tags")
        filter = criterion.to_filter()

        assert filter.operator == FilterOperator.ARRAY_EMPTY
        assert filter.value is None


class TestJsonCriteria:
    """Tests for JSON criteria."""

    def test_json_contains_criterion(self):
        """Test JsonContainsCriterion."""
        criterion = JsonContainsCriterion("metadata", {"key": "value"})
        filter = criterion.to_filter()

        assert filter.operator == FilterOperator.JSON_CONTAINS
        assert filter.value == {"key": "value"}

    def test_json_exists_criterion(self):
        """Test JsonExistsCriterion."""
        criterion = JsonExistsCriterion("settings", {"theme": "dark"})
        filter = criterion.to_filter()

        assert filter.operator == FilterOperator.JSON_EXISTS
        assert filter.value == {"theme": "dark"}

    def test_json_has_key_criterion(self):
        """Test JsonHasKeyCriterion."""
        criterion = JsonHasKeyCriterion("data", "user_id")
        filter = criterion.to_filter()

        assert filter.operator == FilterOperator.JSON_HAS_KEY
        assert filter.value == "user_id"


class TestTemporalCriteria:
    """Tests for temporal/date criteria."""

    def test_date_equals_criterion(self):
        """Test DateEqualsCriterion."""
        test_date = date(2024, 1, 1)
        criterion = DateEqualsCriterion("created_at", test_date)
        filter = criterion.to_filter()

        assert filter.operator == FilterOperator.EQUALS
        assert filter.value == test_date

    def test_date_range_criterion(self):
        """Test DateRangeCriterion."""
        start = date(2024, 1, 1)
        end = date(2024, 12, 31)
        criterion = DateRangeCriterion("created_at", start, end)
        filter = criterion.to_filter()

        assert filter.operator == FilterOperator.BETWEEN
        assert filter.value["start"] == start
        assert filter.value["end"] == end

    def test_after_criterion(self):
        """Test AfterCriterion."""
        after_date = datetime(2024, 1, 1)
        criterion = AfterCriterion("created_at", after_date)
        filter = criterion.to_filter()

        assert filter.operator == FilterOperator.GREATER_THAN
        assert filter.value == after_date

    def test_before_criterion(self):
        """Test BeforeCriterion."""
        before_date = datetime(2024, 12, 31)
        criterion = BeforeCriterion("created_at", before_date)
        filter = criterion.to_filter()

        assert filter.operator == FilterOperator.LESS_THAN
        assert filter.value == before_date

    def test_on_or_after_criterion(self):
        """Test OnOrAfterCriterion."""
        on_or_after = datetime(2024, 1, 1)
        criterion = OnOrAfterCriterion("created_at", on_or_after)
        filter = criterion.to_filter()

        assert filter.operator == FilterOperator.GREATER_EQUAL
        assert filter.value == on_or_after

    def test_on_or_before_criterion(self):
        """Test OnOrBeforeCriterion."""
        on_or_before = datetime(2024, 12, 31)
        criterion = OnOrBeforeCriterion("created_at", on_or_before)
        filter = criterion.to_filter()

        assert filter.operator == FilterOperator.LESS_EQUAL
        assert filter.value == on_or_before

    def test_today_criterion(self):
        """Test TodayCriterion."""
        criterion = TodayCriterion("created_at")
        filter = criterion.to_filter()

        # TodayCriterion uses EQUALS with today's date
        assert filter.operator == FilterOperator.EQUALS
        assert filter.value == date.today()

    def test_yesterday_criterion(self):
        """Test YesterdayCriterion."""
        criterion = YesterdayCriterion("created_at")
        filter = criterion.to_filter()

        # YesterdayCriterion uses EQUALS with yesterday's date
        assert filter.operator == FilterOperator.EQUALS
        assert filter.value == date.today() - timedelta(days=1)

    def test_last_n_days_criterion(self):
        """Test LastNDaysCriterion."""
        criterion = LastNDaysCriterion("created_at", 7)
        filter = criterion.to_filter()

        assert filter.operator == FilterOperator.GREATER_EQUAL
        # Should be approximately 7 days ago
        assert filter.value <= datetime.now()

    def test_last_n_hours_criterion(self):
        """Test LastNHoursCriterion."""
        criterion = LastNHoursCriterion("created_at", 24)
        filter = criterion.to_filter()

        assert filter.operator == FilterOperator.GREATER_EQUAL
        # Should be approximately 24 hours ago
        assert filter.value <= datetime.now()

    def test_this_week_criterion(self):
        """Test ThisWeekCriterion."""
        criterion = ThisWeekCriterion("created_at")
        filter = criterion.to_filter()

        # ThisWeekCriterion uses GREATER_EQUAL from week start (Monday)
        assert filter.operator == FilterOperator.GREATER_EQUAL
        assert filter.value is not None

    def test_this_month_criterion(self):
        """Test ThisMonthCriterion."""
        criterion = ThisMonthCriterion("created_at")
        filter = criterion.to_filter()

        # ThisMonthCriterion uses GREATER_EQUAL from month start
        assert filter.operator == FilterOperator.GREATER_EQUAL
        assert filter.value is not None
        assert filter.value.day == 1

    def test_this_year_criterion(self):
        """Test ThisYearCriterion."""
        criterion = ThisYearCriterion("created_at")
        filter = criterion.to_filter()

        # ThisYearCriterion uses GREATER_EQUAL from year start
        assert filter.operator == FilterOperator.GREATER_EQUAL
        assert filter.value is not None
        assert filter.value.month == 1
        assert filter.value.day == 1


class TestLogicalCriteria:
    """Tests for logical criteria (AND, OR)."""

    def test_and_criterion(self):
        """Test And combinator."""
        c1 = EqualsCriterion("status", "active")
        c2 = GreaterEqualCriterion("age", 18)
        combined = And(c1, c2)

        # And simply wraps multiple criteria
        assert combined is not None
        # The criteria get flattened when building specification

    def test_or_criterion(self):
        """Test Or combinator."""
        c1 = EqualsCriterion("status", "active")
        c2 = EqualsCriterion("status", "pending")
        combined = Or(c1, c2)

        # Or creates a FilterGroup
        filter_group = combined.to_filter_group()
        assert len(filter_group.filters) == 2

    def test_nested_and_or(self):
        """Test nested AND/OR logic."""
        # (status = active OR status = pending) AND age >= 18
        status_criteria = Or(
            EqualsCriterion("status", "active"), EqualsCriterion("status", "pending")
        )
        age_criterion = GreaterEqualCriterion("age", 18)

        combined = And(status_criteria, age_criterion)
        # This tests that complex logic can be composed
        assert combined is not None


class TestCriteriaEdgeCases:
    """Tests for criteria edge cases."""

    def test_criterion_with_none_value(self):
        """Test criterion with None value (for null checks)."""
        criterion = IsNullCriterion("deleted_at")
        filter = criterion.to_filter()

        assert filter.value is None

    def test_criterion_with_empty_list(self):
        """Test InCriterion with empty list."""
        # This should be allowed but might not match anything
        criterion = InCriterion("status", [])
        filter = criterion.to_filter()

        assert filter.value == []

    def test_multiple_and_chaining(self):
        """Test chaining multiple criteria with AND."""
        c1 = EqualsCriterion("status", "active")
        c2 = GreaterEqualCriterion("age", 18)
        c3 = LessThanCriterion("age", 65)

        combined = And(c1, And(c2, c3))
        # Test that complex chaining is supported
        assert combined is not None
