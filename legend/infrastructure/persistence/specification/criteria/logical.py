"""Logical criteria.

This module defines criteria for logical operations (AND, OR).
"""

from typing import List

from .base import Criterion, CompositeCriterion
from ..core import Filter, FilterGroup, LogicalOperator

class AndCriterion(CompositeCriterion):
    """Criterion for AND operation."""
    
    def __init__(self, criteria: List[Criterion]):
        """Initialize AND criterion.
        
        Args:
            criteria: List of criteria to combine
        """
        if not criteria:
            raise ValueError("Must provide at least one criterion")
        if not all(isinstance(c, Criterion) for c in criteria):
            raise ValueError("All items must be valid criteria")
            
        self.criteria = criteria
        super().__init__(criteria, LogicalOperator.AND)
    
    def to_filter(self) -> Filter:
        if len(self.criteria) == 1:
            return self.criteria[0].to_filter()
        return self.to_filter_group().filters[0]

    def to_filter_group(self) -> FilterGroup:
        """Convert to filter group.
        
        Returns:
            Filter group with AND operator
        """
        return FilterGroup(
            filters=[c.to_filter() for c in self.criteria],
            operator=LogicalOperator.AND
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AndCriterion):
            return False
        return self.criteria == other.criteria

class OrCriterion(CompositeCriterion):
    """Criterion for OR operation."""
    
    def __init__(self, criteria: List[Criterion]):
        """Initialize OR criterion.
        
        Args:
            criteria: List of criteria to combine
        """
        if not criteria:
            raise ValueError("Must provide at least one criterion")
        if not all(isinstance(c, Criterion) for c in criteria):
            raise ValueError("All items must be valid criteria")
            
        self.criteria = criteria
        super().__init__(criteria, LogicalOperator.OR)
    
    def to_filter(self) -> Filter:
        if len(self.criteria) == 1:
            return self.criteria[0].to_filter()
        return self.to_filter_group().filters[0]

    def to_filter_group(self) -> FilterGroup:
        """Convert to filter group.
        
        Returns:
            Filter group with OR operator
        """
        return FilterGroup(
            filters=[c.to_filter() for c in self.criteria],
            operator=LogicalOperator.OR
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, OrCriterion):
            return False
        return self.criteria == other.criteria 