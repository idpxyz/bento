"""Temporal criteria.

This module defines criteria for temporal queries.
"""

from datetime import datetime, timedelta
from typing import Optional

from .base import Criterion, CompositeCriterion
from ..core import Filter, FilterOperator, LogicalOperator

class DateRangeCriterion(Criterion):
    """Date range criterion for filtering by date fields."""
    
    def __init__(self, field: str, start_date: datetime, end_date: datetime):
        """Initialize date range criterion.
        
        Args:
            field: Field name to filter on
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
        """
        if not field:
            raise ValueError("Field name cannot be empty")
        if not isinstance(start_date, datetime):
            raise ValueError("Start date must be a datetime object")
        if not isinstance(end_date, datetime):
            raise ValueError("End date must be a datetime object")
        if start_date > end_date:
            raise ValueError("Start date cannot be after end date")
            
        self.field = field
        self.start_date = start_date
        self.end_date = end_date
    
    def to_filter(self) -> Filter:
        """Convert to filter.
        
        Returns:
            Filter with BETWEEN operator and date range value
        """
        return Filter(
            field=self.field,
            operator=FilterOperator.BETWEEN,
            value={
                "start": self.start_date,
                "end": self.end_date
            }
        )
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, DateRangeCriterion):
            return False
        return (
            self.field == other.field and
            self.start_date == other.start_date and
            self.end_date == other.end_date
        )

class DateCriterion(Criterion):
    """Criterion for date comparison."""
    
    def __init__(self, field: str, date: datetime, operator: FilterOperator):
        self.field = field
        self.date = date
        self.operator = operator
    
    def to_filter(self) -> Filter:
        return Filter(
            field=self.field,
            operator=self.operator,
            value=self.date
        )

class RelativeDateCriterion(Criterion):
    """Criterion for relative date queries (e.g., last 7 days)."""
    
    def __init__(
        self,
        field: str,
        days: Optional[int] = None,
        reference_date: Optional[datetime] = None
    ):
        self.field = field
        self.days = days
        self.reference_date = reference_date or datetime.now()
    
    def to_filter(self) -> Filter:
        if self.days is not None:
            target_date = self.reference_date - timedelta(days=self.days)
        else:
            target_date = self.reference_date
            
        return Filter(
            field=self.field,
            operator=FilterOperator.GREATER_EQUAL,
            value=target_date
        ) 