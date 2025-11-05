"""Specification pattern core components.

This module provides the core building blocks for the specification pattern:
- Type definitions (Filter, Sort, Page, etc.)
- Base specification interface
- Composite specification implementation
"""

from .base import CompositeSpecification
from .types import (
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

__all__ = [
    # Core specification
    "CompositeSpecification",
    # Types
    "Filter",
    "FilterGroup",
    "FilterOperator",
    "LogicalOperator",
    "Sort",
    "SortDirection",
    "PageParams",
    "Page",
    "Statistic",
    "StatisticalFunction",
    "Having",
]

