"""Aggregate specification builder.

This module defines the builder for aggregate specifications.
"""

from typing import TypeVar

from idp.framework.domain.model.aggregate import AggregateRoot
from .entity import EntitySpecificationBuilder
from ..criteria.comparison import EqualsCriterion, ComparisonCriterion
from ..core import FilterOperator

T = TypeVar('T', bound=AggregateRoot)

class AggregateSpecificationBuilder(EntitySpecificationBuilder[T]):
    """Builder for aggregate specifications.
    
    This builder extends the entity specification builder with aggregate-specific
    query patterns:
    - Version queries
    - Event state queries
    - Aggregate type queries
    """
    
    def by_version(self, version: int) -> 'AggregateSpecificationBuilder[T]':
        """Add version filter.
        
        Args:
            version: Version number to match
            
        Returns:
            Self for method chaining
        """
        return self.add_criterion(EqualsCriterion('version', version))
    
    def version_greater_than(self, version: int) -> 'AggregateSpecificationBuilder[T]':
        """Add version greater than filter.
        
        Args:
            version: Version number to compare against
            
        Returns:
            Self for method chaining
        """
        return self.add_criterion(
            ComparisonCriterion('version', version, FilterOperator.GREATER_THAN)
        )
    
    def version_less_than(self, version: int) -> 'AggregateSpecificationBuilder[T]':
        """Add version less than filter.
        
        Args:
            version: Version number to compare against
            
        Returns:
            Self for method chaining
        """
        return self.add_criterion(
            ComparisonCriterion('version', version, FilterOperator.LESS_THAN)
        )
    
    def has_uncommitted_events(self) -> 'AggregateSpecificationBuilder[T]':
        """Add uncommitted events filter.
        
        Returns:
            Self for method chaining
        """
        return self.add_criterion(
            EqualsCriterion('has_uncommitted_events', True)
        )
    
    def by_type(self, aggregate_type: str) -> 'AggregateSpecificationBuilder[T]':
        """Add aggregate type filter.
        
        Args:
            aggregate_type: Aggregate type to match
            
        Returns:
            Self for method chaining
        """
        return self.add_criterion(
            EqualsCriterion('type', aggregate_type)
        ) 