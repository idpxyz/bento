"""Temporal (time-based) criteria for date and datetime queries.

This module provides specialized criteria for working with date and time fields,
including common temporal operations like date ranges, relative dates, etc.
"""

from datetime import date, datetime, timedelta

from ..core import Filter, FilterOperator
from .base import Criterion
from .comparison import BetweenCriterion


class DateEqualsCriterion(Criterion):
    """Criterion for exact date match."""

    __slots__ = ("_field", "_date")

    def __init__(self, field: str, target_date: date | datetime) -> None:
        """Initialize date equals criterion.

        Args:
            field: Date/datetime field to compare
            target_date: Target date to match
        """
        self._field = field
        self._date = target_date

    def to_filter(self) -> Filter:
        """Convert to Filter."""
        return Filter(field=self._field, operator=FilterOperator.EQUALS, value=self._date)


class DateRangeCriterion(BetweenCriterion[date | datetime]):
    """Criterion for date range check."""

    def __init__(self, field: str, start: date | datetime, end: date | datetime) -> None:
        """Initialize date range criterion.

        Args:
            field: Date/datetime field to check
            start: Start date (inclusive)
            end: End date (inclusive)
        """
        super().__init__(field, start, end)


class AfterCriterion(Criterion):
    """Criterion for dates after a given date (exclusive)."""

    __slots__ = ("_field", "_date")

    def __init__(self, field: str, after_date: date | datetime) -> None:
        """Initialize after criterion.

        Args:
            field: Date/datetime field to check
            after_date: Date to compare against (exclusive)
        """
        self._field = field
        self._date = after_date

    def to_filter(self) -> Filter:
        """Convert to Filter."""
        return Filter(field=self._field, operator=FilterOperator.GREATER_THAN, value=self._date)


class BeforeCriterion(Criterion):
    """Criterion for dates before a given date (exclusive)."""

    __slots__ = ("_field", "_date")

    def __init__(self, field: str, before_date: date | datetime) -> None:
        """Initialize before criterion.

        Args:
            field: Date/datetime field to check
            before_date: Date to compare against (exclusive)
        """
        self._field = field
        self._date = before_date

    def to_filter(self) -> Filter:
        """Convert to Filter."""
        return Filter(field=self._field, operator=FilterOperator.LESS_THAN, value=self._date)


class OnOrAfterCriterion(Criterion):
    """Criterion for dates on or after a given date (inclusive)."""

    __slots__ = ("_field", "_date")

    def __init__(self, field: str, on_or_after: date | datetime) -> None:
        """Initialize on or after criterion.

        Args:
            field: Date/datetime field to check
            on_or_after: Date to compare against (inclusive)
        """
        self._field = field
        self._date = on_or_after

    def to_filter(self) -> Filter:
        """Convert to Filter."""
        return Filter(field=self._field, operator=FilterOperator.GREATER_EQUAL, value=self._date)


class OnOrBeforeCriterion(Criterion):
    """Criterion for dates on or before a given date (inclusive)."""

    __slots__ = ("_field", "_date")

    def __init__(self, field: str, on_or_before: date | datetime) -> None:
        """Initialize on or before criterion.

        Args:
            field: Date/datetime field to check
            on_or_before: Date to compare against (inclusive)
        """
        self._field = field
        self._date = on_or_before

    def to_filter(self) -> Filter:
        """Convert to Filter."""
        return Filter(field=self._field, operator=FilterOperator.LESS_EQUAL, value=self._date)


class TodayCriterion(Criterion):
    """Criterion for matching today's date."""

    __slots__ = ("_field",)

    def __init__(self, field: str) -> None:
        """Initialize today criterion.

        Args:
            field: Date/datetime field to check
        """
        self._field = field

    def to_filter(self) -> Filter:
        """Convert to Filter."""
        today = date.today()
        return Filter(field=self._field, operator=FilterOperator.EQUALS, value=today)


class YesterdayCriterion(Criterion):
    """Criterion for matching yesterday's date."""

    __slots__ = ("_field",)

    def __init__(self, field: str) -> None:
        """Initialize yesterday criterion.

        Args:
            field: Date/datetime field to check
        """
        self._field = field

    def to_filter(self) -> Filter:
        """Convert to Filter."""
        yesterday = date.today() - timedelta(days=1)
        return Filter(field=self._field, operator=FilterOperator.EQUALS, value=yesterday)


class LastNDaysCriterion(Criterion):
    """Criterion for matching dates within the last N days."""

    __slots__ = ("_field", "_days")

    def __init__(self, field: str, days: int) -> None:
        """Initialize last N days criterion.

        Args:
            field: Date/datetime field to check
            days: Number of days to look back
        """
        self._field = field
        self._days = days

    def to_filter(self) -> Filter:
        """Convert to Filter."""
        start_date = datetime.now() - timedelta(days=self._days)
        return Filter(
            field=self._field,
            operator=FilterOperator.GREATER_EQUAL,
            value=start_date,
        )


class LastNHoursCriterion(Criterion):
    """Criterion for matching datetimes within the last N hours."""

    __slots__ = ("_field", "_hours")

    def __init__(self, field: str, hours: int) -> None:
        """Initialize last N hours criterion.

        Args:
            field: Datetime field to check
            hours: Number of hours to look back
        """
        self._field = field
        self._hours = hours

    def to_filter(self) -> Filter:
        """Convert to Filter."""
        start_time = datetime.now() - timedelta(hours=self._hours)
        return Filter(
            field=self._field,
            operator=FilterOperator.GREATER_EQUAL,
            value=start_time,
        )


class ThisWeekCriterion(Criterion):
    """Criterion for matching dates in the current week."""

    __slots__ = ("_field",)

    def __init__(self, field: str) -> None:
        """Initialize this week criterion.

        Args:
            field: Date/datetime field to check
        """
        self._field = field

    def to_filter(self) -> Filter:
        """Convert to Filter."""
        today = date.today()
        # Monday is 0, Sunday is 6
        days_since_monday = today.weekday()
        week_start = today - timedelta(days=days_since_monday)
        return Filter(
            field=self._field,
            operator=FilterOperator.GREATER_EQUAL,
            value=week_start,
        )


class ThisMonthCriterion(Criterion):
    """Criterion for matching dates in the current month."""

    __slots__ = ("_field",)

    def __init__(self, field: str) -> None:
        """Initialize this month criterion.

        Args:
            field: Date/datetime field to check
        """
        self._field = field

    def to_filter(self) -> Filter:
        """Convert to Filter."""
        today = date.today()
        month_start = date(today.year, today.month, 1)
        return Filter(
            field=self._field,
            operator=FilterOperator.GREATER_EQUAL,
            value=month_start,
        )


class ThisYearCriterion(Criterion):
    """Criterion for matching dates in the current year."""

    __slots__ = ("_field",)

    def __init__(self, field: str) -> None:
        """Initialize this year criterion.

        Args:
            field: Date/datetime field to check
        """
        self._field = field

    def to_filter(self) -> Filter:
        """Convert to Filter."""
        today = date.today()
        year_start = date(today.year, 1, 1)
        return Filter(
            field=self._field,
            operator=FilterOperator.GREATER_EQUAL,
            value=year_start,
        )
