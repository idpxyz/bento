"""Criteria module for type-safe query condition building.

This module provides high-level criteria for building queries in a type-safe,
composable manner. Criteria can be combined and converted to Filters for use in Specifications.
"""

from .base import AndCriterion, CompositeCriterion, Criterion, OrCriterion
from .comparison import (
    ArrayContainsCriterion,
    ArrayEmptyCriterion,
    ArrayOverlapsCriterion,
    BetweenCriterion,
    ContainsCriterion,
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
    LessEqualCriterion,
    LessThanCriterion,
    LikeCriterion,
    NotEqualsCriterion,
    NotInCriterion,
    NullCriterion,
    RegexCriterion,
    StartsWithCriterion,
)
from .logical import And, Or, to_filter_group
from .temporal import (
    AfterCriterion,
    BeforeCriterion,
    DateEqualsCriterion,
    DateRangeCriterion,
    LastNDaysCriterion,
    LastNHoursCriterion,
    OnOrAfterCriterion,
    OnOrBeforeCriterion,
    ThisMonthCriterion,
    ThisWeekCriterion,
    ThisYearCriterion,
    TodayCriterion,
    YesterdayCriterion,
)

__all__ = [
    # Base
    "Criterion",
    "CompositeCriterion",
    "AndCriterion",
    "OrCriterion",
    # Logical combinators
    "And",
    "Or",
    "to_filter_group",
    # Comparison
    "EqualsCriterion",
    "NotEqualsCriterion",
    "GreaterThanCriterion",
    "GreaterEqualCriterion",
    "LessThanCriterion",
    "LessEqualCriterion",
    "BetweenCriterion",
    "InCriterion",
    "NotInCriterion",
    "NullCriterion",
    "IsNullCriterion",
    "IsNotNullCriterion",
    # Text
    "LikeCriterion",
    "ILikeCriterion",
    "ContainsCriterion",
    "IContainsCriterion",
    "StartsWithCriterion",
    "EndsWithCriterion",
    "RegexCriterion",
    # Array
    "ArrayContainsCriterion",
    "ArrayOverlapsCriterion",
    "ArrayEmptyCriterion",
    # JSON
    "JsonContainsCriterion",
    "JsonExistsCriterion",
    "JsonHasKeyCriterion",
    # Temporal
    "DateEqualsCriterion",
    "DateRangeCriterion",
    "AfterCriterion",
    "BeforeCriterion",
    "OnOrAfterCriterion",
    "OnOrBeforeCriterion",
    "TodayCriterion",
    "YesterdayCriterion",
    "LastNDaysCriterion",
    "LastNHoursCriterion",
    "ThisWeekCriterion",
    "ThisMonthCriterion",
    "ThisYearCriterion",
]
