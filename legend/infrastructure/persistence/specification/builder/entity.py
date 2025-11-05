"""Entity specification builder.

This module defines the builder for entity specifications.
"""

from datetime import datetime, timedelta
from typing import TypeVar, Optional

from idp.framework.domain.model import Entity
from .base import SpecificationBuilder
from ..criteria.comparison import EqualsCriterion
from ..criteria.temporal import DateRangeCriterion, RelativeDateCriterion

T = TypeVar('T', bound=Entity)

class EntitySpecificationBuilder(SpecificationBuilder[T]):
    """Builder for entity specifications.
    
    This builder provides common query patterns for entities:
    - Status queries
    - Temporal queries
    - Flag queries
    """
    
    def by_status(self, status: str) -> 'EntitySpecificationBuilder[T]':
        """Add status filter.
        
        Args:
            status: Status value to match
            
        Returns:
            Self for method chaining
        """
        return self.add_criterion(EqualsCriterion('status', status))
    
    def is_active(self, active: bool = True) -> 'EntitySpecificationBuilder[T]':
        """Add active status filter.
        
        Args:
            active: Active status to match
            
        Returns:
            Self for method chaining
        """
        return self.add_criterion(EqualsCriterion('is_active', active))
    
    def is_deleted(self, deleted: bool = False) -> 'EntitySpecificationBuilder[T]':
        """Add deleted status filter.
        
        Args:
            deleted: Deleted status to match
            
        Returns:
            Self for method chaining
        """
        return self.add_criterion(EqualsCriterion('is_deleted', deleted))
    
    def created_between(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> 'EntitySpecificationBuilder[T]':
        """Add creation date range filter.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            Self for method chaining
        """
        return self.add_criterion(
            DateRangeCriterion('created_at', start_date, end_date)
        )
    
    def created_after(
        self,
        date: datetime
    ) -> 'EntitySpecificationBuilder[T]':
        """Add creation date filter.
        
        Args:
            date: Specific date
            
        Returns:
            Self for method chaining
        """
        return self.add_criterion(
            RelativeDateCriterion('created_at', None, date)
        )
    
    def updated_between(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> 'EntitySpecificationBuilder[T]':
        """Add update date range filter.
        
        Args:
            start_date: Start of date range
            end_date: End of date range
            
        Returns:
            Self for method chaining
        """
        return self.add_criterion(
            DateRangeCriterion('updated_at', start_date, end_date)
        )
    
    def by_tenant(self, tenant_id: str) -> 'EntitySpecificationBuilder[T]':
        """Add tenant filter.
        
        Args:
            tenant_id: Tenant ID to match
            
        Returns:
            Self for method chaining
        """
        return self.add_criterion(EqualsCriterion('tenant_id', str(tenant_id)))

    def created_before(self, date: datetime) -> 'EntitySpecificationBuilder[T]':
        """Add creation date filter.
        
        Args:
            date: Specific date
            
        Returns:
            Self for method chaining
        """
        return self.add_criterion(
            RelativeDateCriterion('created_at', None, date, "<=")
        )

    def created_in_last_days(self, days: int) -> 'EntitySpecificationBuilder[T]':
        """Add creation date filter.
        
        Args:
            days: Number of days ago
            
        Returns:
            Self for method chaining
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        return self.created_between(start_date, end_date)

    def updated_in_last_days(self, days: int) -> 'EntitySpecificationBuilder[T]':
        """Add update date filter.
        
        Args:
            days: Number of days ago
            
        Returns:
            Self for method chaining
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        return self.updated_between(start_date, end_date)

    def created_in_month(self, year: int, month: int) -> 'EntitySpecificationBuilder[T]':
        """Add creation date filter.
        
        Args:
            year: Year
            month: Month
            
        Returns:
            Self for method chaining
        """
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        return self.created_between(start_date, end_date) 