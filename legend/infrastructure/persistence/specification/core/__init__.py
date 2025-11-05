"""
Core specification pattern package.

This package provides the core types and interfaces for implementing
the specification pattern.
"""

from .base import CompositeSpecification, Specification
from .type import (
    FieldList,
    Filter,
    FilterGroup,
    FilterList,
    FilterOperator,
    FilterValue,
    GroupList,
    Having,
    HavingList,
    LogicalOperator,
    Page,
    PageParams,
    Sort,
    SortList,
    Statistic,
    StatisticalFunction,
    StatisticList,
    ExistsSpec,
    NotExistsSpec
)

__all__ = [
    # Enums
    'FilterOperator',
    'LogicalOperator',
    'StatisticalFunction',

    # Data classes
    'Filter',
    'Sort',
    'PageParams'
    'Page',
    'FilterGroup',
    'Statistic',
    'Having',

    # Type aliases
    'FilterValue',
    'SortList',
    'FilterList',
    'GroupList',
    'StatisticList',
    'HavingList',
    'FieldList',

    # Base classes
    'Specification',
    'CompositeSpecification',

    'ExistsSpec',
    'NotExistsSpec'
]
