"""Base criteria interfaces and classes."""

from abc import ABC, abstractmethod
from typing import List

from ..core import Filter,FilterGroup,LogicalOperator

class Criterion(ABC):
    """Base interface for all criteria."""
    
    @abstractmethod
    def to_filter(self) -> Filter:
        """Convert criterion to a filter."""
        pass

class CompositeCriterion(Criterion):
    """Base class for composite criteria."""
    
    def __init__(self, criteria: List[Criterion], operator: LogicalOperator):
        self.criteria = criteria
        self.operator = operator
    
    def to_filter_group(self) -> FilterGroup:
        """Convert composite criterion to a filter group.
        
        Returns:
            FilterGroup containing all child criteria filters
        """
        return FilterGroup(
            filters=[c.to_filter() for c in self.criteria],
            operator=self.operator
        ) 