"""Comparison criteria for building type-safe query conditions.

This module provides various comparison criteria for common query operations:
- Equality and inequality
- Range comparisons (greater than, less than, etc.)
- Collection operations (IN, NOT IN)
- Range checks (BETWEEN)
- Null checks
- Text search (LIKE, ILIKE, CONTAINS, etc.)
- Pattern matching (regex)
- Array operations
- JSON operations
"""

from typing import Any

from ..core import Filter, FilterOperator
from .base import Criterion


class ComparisonCriterion(Criterion):
    """Base class for comparison criteria.

    Provides common implementation for simple field-operator-value comparisons.
    """

    __slots__ = ("_field", "_value", "_operator")

    def __init__(self, field: str, value: Any, operator: FilterOperator) -> None:
        """Initialize comparison criterion.

        Args:
            field: Field to compare
            value: Value to compare against
            operator: Comparison operator to use
        """
        self._field = field
        self._value = value
        self._operator = operator

    def to_filter(self) -> Filter:
        """Convert to Filter."""
        return Filter(field=self._field, operator=self._operator, value=self._value)


# ==================== Equality Comparisons ====================


class EqualsCriterion(ComparisonCriterion):
    """Criterion for equality comparison (field = value)."""

    def __init__(self, field: str, value: Any) -> None:
        """Initialize equals criterion.

        Args:
            field: Field to compare
            value: Value to match
        """
        super().__init__(field, value, FilterOperator.EQUALS)


class NotEqualsCriterion(ComparisonCriterion):
    """Criterion for inequality comparison (field != value)."""

    def __init__(self, field: str, value: Any) -> None:
        """Initialize not equals criterion.

        Args:
            field: Field to compare
            value: Value to exclude
        """
        super().__init__(field, value, FilterOperator.NOT_EQUALS)


# ==================== Range Comparisons ====================


class GreaterThanCriterion(ComparisonCriterion):
    """Criterion for greater than comparison (field > value)."""

    def __init__(self, field: str, value: Any) -> None:
        """Initialize greater than criterion.

        Args:
            field: Field to compare
            value: Lower bound (exclusive)
        """
        super().__init__(field, value, FilterOperator.GREATER_THAN)


class GreaterEqualCriterion(ComparisonCriterion):
    """Criterion for greater than or equal comparison (field >= value)."""

    def __init__(self, field: str, value: Any) -> None:
        """Initialize greater or equal criterion.

        Args:
            field: Field to compare
            value: Lower bound (inclusive)
        """
        super().__init__(field, value, FilterOperator.GREATER_EQUAL)


class LessThanCriterion(ComparisonCriterion):
    """Criterion for less than comparison (field < value)."""

    def __init__(self, field: str, value: Any) -> None:
        """Initialize less than criterion.

        Args:
            field: Field to compare
            value: Upper bound (exclusive)
        """
        super().__init__(field, value, FilterOperator.LESS_THAN)


class LessEqualCriterion(ComparisonCriterion):
    """Criterion for less than or equal comparison (field <= value)."""

    def __init__(self, field: str, value: Any) -> None:
        """Initialize less or equal criterion.

        Args:
            field: Field to compare
            value: Upper bound (inclusive)
        """
        super().__init__(field, value, FilterOperator.LESS_EQUAL)


class BetweenCriterion[T](ComparisonCriterion):
    """Criterion for BETWEEN range check (start <= field <= end)."""

    def __init__(self, field: str, start: T, end: T) -> None:
        """Initialize between criterion.

        Args:
            field: Field to compare
            start: Start value of the range (inclusive)
            end: End value of the range (inclusive)
        """
        super().__init__(field, {"start": start, "end": end}, FilterOperator.BETWEEN)


# ==================== Collection Operations ====================


class InCriterion(ComparisonCriterion):
    """Criterion for IN comparison (field IN values)."""

    def __init__(self, field: str, values: list[Any]) -> None:
        """Initialize IN criterion.

        Args:
            field: Field to check
            values: List of values to match against
        """
        super().__init__(field, values, FilterOperator.IN)


class NotInCriterion(ComparisonCriterion):
    """Criterion for NOT IN comparison (field NOT IN values)."""

    def __init__(self, field: str, values: list[Any]) -> None:
        """Initialize NOT IN criterion.

        Args:
            field: Field to check
            values: List of values to exclude
        """
        super().__init__(field, values, FilterOperator.NOT_IN)


# ==================== Null Checks ====================


class NullCriterion(ComparisonCriterion):
    """Criterion for NULL/NOT NULL checks."""

    def __init__(self, field: str, is_null: bool = True) -> None:
        """Initialize null check criterion.

        Args:
            field: Field to check
            is_null: True for IS NULL, False for IS NOT NULL
        """
        operator = FilterOperator.IS_NULL if is_null else FilterOperator.IS_NOT_NULL
        super().__init__(field, None, operator)


class IsNullCriterion(NullCriterion):
    """Criterion for IS NULL check."""

    def __init__(self, field: str) -> None:
        """Initialize IS NULL criterion.

        Args:
            field: Field to check for NULL
        """
        super().__init__(field, is_null=True)


class IsNotNullCriterion(NullCriterion):
    """Criterion for IS NOT NULL check."""

    def __init__(self, field: str) -> None:
        """Initialize IS NOT NULL criterion.

        Args:
            field: Field to check for NOT NULL
        """
        super().__init__(field, is_null=False)


# ==================== Text Search ====================


class LikeCriterion(ComparisonCriterion):
    """Criterion for LIKE text pattern matching (case-sensitive)."""

    def __init__(self, field: str, pattern: str) -> None:
        """Initialize LIKE criterion.

        Args:
            field: Field to search
            pattern: Pattern to match (use % as wildcard)
        """
        super().__init__(field, pattern, FilterOperator.LIKE)


class ILikeCriterion(ComparisonCriterion):
    """Criterion for ILIKE text pattern matching (case-insensitive)."""

    def __init__(self, field: str, pattern: str) -> None:
        """Initialize ILIKE criterion.

        Args:
            field: Field to search
            pattern: Pattern to match (use % as wildcard)
        """
        super().__init__(field, pattern, FilterOperator.ILIKE)


class ContainsCriterion(ComparisonCriterion):
    """Criterion for text containment check (case-sensitive)."""

    def __init__(self, field: str, text: str) -> None:
        """Initialize contains criterion.

        Args:
            field: Field to search
            text: Text to find
        """
        super().__init__(field, f"%{text}%", FilterOperator.LIKE)


class IContainsCriterion(ComparisonCriterion):
    """Criterion for text containment check (case-insensitive)."""

    def __init__(self, field: str, text: str) -> None:
        """Initialize case-insensitive contains criterion.

        Args:
            field: Field to search
            text: Text to find
        """
        super().__init__(field, f"%{text}%", FilterOperator.ILIKE)


class StartsWithCriterion(ComparisonCriterion):
    """Criterion for prefix matching."""

    def __init__(self, field: str, prefix: str, case_sensitive: bool = True) -> None:
        """Initialize starts with criterion.

        Args:
            field: Field to search
            prefix: Prefix to match
            case_sensitive: Whether to perform case-sensitive match
        """
        operator = FilterOperator.LIKE if case_sensitive else FilterOperator.ILIKE
        super().__init__(field, f"{prefix}%", operator)


class EndsWithCriterion(ComparisonCriterion):
    """Criterion for suffix matching."""

    def __init__(self, field: str, suffix: str, case_sensitive: bool = True) -> None:
        """Initialize ends with criterion.

        Args:
            field: Field to search
            suffix: Suffix to match
            case_sensitive: Whether to perform case-sensitive match
        """
        operator = FilterOperator.LIKE if case_sensitive else FilterOperator.ILIKE
        super().__init__(field, f"%{suffix}", operator)


class RegexCriterion(ComparisonCriterion):
    """Criterion for regex pattern matching."""

    def __init__(self, field: str, pattern: str, case_sensitive: bool = True) -> None:
        """Initialize regex criterion.

        Args:
            field: Field to search
            pattern: Regular expression pattern
            case_sensitive: Whether to perform case-sensitive match
        """
        operator = FilterOperator.REGEX if case_sensitive else FilterOperator.IREGEX
        super().__init__(field, pattern, operator)


# ==================== Array Operations ====================


class ArrayContainsCriterion(ComparisonCriterion):
    """Criterion for array containment check (array contains all values)."""

    def __init__(self, field: str, values: list[Any]) -> None:
        """Initialize array contains criterion.

        Args:
            field: Array field to check
            values: Values that array should contain
        """
        super().__init__(field, values, FilterOperator.ARRAY_CONTAINS)


class ArrayOverlapsCriterion(ComparisonCriterion):
    """Criterion for array overlap check (array contains any value)."""

    def __init__(self, field: str, values: list[Any]) -> None:
        """Initialize array overlaps criterion.

        Args:
            field: Array field to check
            values: Values to check for overlap
        """
        super().__init__(field, values, FilterOperator.ARRAY_OVERLAPS)


class ArrayEmptyCriterion(ComparisonCriterion):
    """Criterion for array emptiness check."""

    def __init__(self, field: str, is_empty: bool = True) -> None:
        """Initialize array empty criterion.

        Args:
            field: Array field to check
            is_empty: True for empty check, False for non-empty check
        """
        operator = FilterOperator.ARRAY_EMPTY if is_empty else FilterOperator.ARRAY_NOT_EMPTY
        super().__init__(field, None, operator)


# ==================== JSON Operations ====================


class JsonContainsCriterion(ComparisonCriterion):
    """Criterion for JSON containment check."""

    def __init__(self, field: str, value: dict[str, Any] | list[Any]) -> None:
        """Initialize JSON contains criterion.

        Args:
            field: JSON field to check
            value: JSON value that should be contained
        """
        super().__init__(field, value, FilterOperator.JSON_CONTAINS)


class JsonExistsCriterion(ComparisonCriterion):
    """Criterion for JSON path existence check."""

    def __init__(self, field: str, path: dict[str, Any] | list[Any]) -> None:
        """Initialize JSON exists criterion.

        Args:
            field: JSON field to check
            path: JSON path that should exist
        """
        super().__init__(field, path, FilterOperator.JSON_EXISTS)


class JsonHasKeyCriterion(ComparisonCriterion):
    """Criterion for JSON key existence check."""

    def __init__(self, field: str, key: str) -> None:
        """Initialize JSON has key criterion.

        Args:
            field: JSON field to check
            key: Key that should exist in JSON
        """
        super().__init__(field, key, FilterOperator.JSON_HAS_KEY)
