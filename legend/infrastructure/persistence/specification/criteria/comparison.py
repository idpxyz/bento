"""Comparison criteria.

This module defines criteria for comparison operations.
"""

from typing import Any, List, Union, TypeVar, Generic, Dict, Optional

from .base import Criterion
from ..core import Filter, FilterOperator

T = TypeVar('T')

class ComparisonCriterion(Criterion):
    """Base class for comparison criteria."""
    
    def __init__(self, field: str, value: Any, operator: FilterOperator):
        """Initialize comparison criterion.
        
        Args:
            field: Field to compare
            value: Value to compare against
            operator: Comparison operator to use
        """
        self.field = field
        self.value = value
        self.operator = operator
    
    def to_filter(self) -> Filter:
        return Filter(
            field=self.field,
            operator=self.operator,
            value=self.value
        )

class BetweenCriterion(Generic[T], Criterion):
    """Criterion for BETWEEN comparisons."""
    
    def __init__(self, field: str, start: T, end: T):
        """Initialize between criterion.
        
        Args:
            field: Field to compare
            start: Start value of the range
            end: End value of the range
        """
        self.field = field
        self.start = start
        self.end = end
    
    def to_filter(self) -> Filter:
        return Filter(
            field=self.field,
            operator=FilterOperator.BETWEEN,
            value={'start': self.start, 'end': self.end}
        )

class EqualsCriterion(ComparisonCriterion):
    """Criterion for equality comparison."""
    
    def __init__(self, field: str, value: Any):
        super().__init__(field, value, FilterOperator.EQUALS)

class InCriterion(ComparisonCriterion):
    """Criterion for IN comparison."""
    
    def __init__(self, field: str, values: List[Any]):
        super().__init__(field, values, FilterOperator.IN)

class TextSearchCriterion(ComparisonCriterion):
    """Criterion for text search."""
    
    def __init__(self, field: str, text: str, case_sensitive: bool = False):
        operator = FilterOperator.LIKE if case_sensitive else FilterOperator.ILIKE
        super().__init__(field, f"%{text}%", operator)

class NullCriterion(ComparisonCriterion):
    """Criterion for NULL checks."""
    
    def __init__(self, field: str, is_null: bool = True):
        operator = FilterOperator.IS_NULL if is_null else FilterOperator.IS_NOT_NULL
        super().__init__(field, None, operator)

class RegexCriterion(ComparisonCriterion):
    """Criterion for regex pattern matching."""
    
    def __init__(self, field: str, pattern: str, case_sensitive: bool = True):
        operator = FilterOperator.REGEX if case_sensitive else FilterOperator.IREGEX
        super().__init__(field, pattern, operator)

class ArrayContainsCriterion(ComparisonCriterion):
    """Criterion for array containment check."""
    
    def __init__(self, field: str, values: List[Any]):
        super().__init__(field, values, FilterOperator.ARRAY_CONTAINS)

class ArrayOverlapsCriterion(ComparisonCriterion):
    """Criterion for array overlap check."""
    
    def __init__(self, field: str, values: List[Any]):
        super().__init__(field, values, FilterOperator.ARRAY_OVERLAPS)

class ArrayEmptyCriterion(ComparisonCriterion):
    """Criterion for array emptiness check."""
    
    def __init__(self, field: str, is_empty: bool = True):
        operator = FilterOperator.ARRAY_EMPTY if is_empty else FilterOperator.ARRAY_NOT_EMPTY
        super().__init__(field, None, operator)

class JsonContainsCriterion(ComparisonCriterion):
    """Criterion for JSON containment check."""
    
    def __init__(self, field: str, value: Union[Dict, List]):
        super().__init__(field, value, FilterOperator.JSON_CONTAINS)

class JsonExistsCriterion(ComparisonCriterion):
    """Criterion for JSON path existence check."""
    
    def __init__(self, field: str, path: Union[Dict, List]):
        super().__init__(field, path, FilterOperator.JSON_EXISTS)

class JsonHasKeyCriterion(ComparisonCriterion):
    """Criterion for JSON key existence check."""
    
    def __init__(self, field: str, key: str):
        super().__init__(field, key, FilterOperator.JSON_HAS_KEY) 
        