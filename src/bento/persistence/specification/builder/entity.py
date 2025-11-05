"""Entity specification builder with common entity query patterns.

This module provides specialized builders for entity-specific queries,
including common patterns like status filtering, temporal queries, etc.
"""

from datetime import date, datetime, timedelta
from typing import Any, Self, TypeVar

from bento.domain.entity import Entity

from ..criteria import (
    DateRangeCriterion,
    EqualsCriterion,
    LastNDaysCriterion,
    OnOrAfterCriterion,
    OnOrBeforeCriterion,
)
from .base import SpecificationBuilder

T = TypeVar("T", bound=Entity)


class EntitySpecificationBuilder(SpecificationBuilder[T]):
    """Builder for entity specifications with common entity patterns.

    This builder provides convenient methods for common entity query patterns:
    - Status queries (active, deleted, etc.)
    - Temporal queries (created_at, updated_at)
    - Flag queries (is_active, is_deleted)
    - Tenant queries

    Example:
        ```python
        spec = (EntitySpecificationBuilder()
            .is_active()
            .created_in_last_days(30)
            .order_by("created_at", "desc")
            .build())
        ```
    """

    def by_id(self, entity_id: Any) -> Self:
        """Filter by entity ID.

        Args:
            entity_id: Entity ID to match

        Returns:
            Self for method chaining
        """
        return self.add_criterion(EqualsCriterion("id", str(entity_id)))

    def by_status(self, status: str) -> Self:
        """Filter by status.

        Args:
            status: Status value to match

        Returns:
            Self for method chaining
        """
        return self.add_criterion(EqualsCriterion("status", status))

    def is_active(self, active: bool = True) -> Self:
        """Filter by active status.

        Args:
            active: Active status to match (default: True)

        Returns:
            Self for method chaining
        """
        return self.add_criterion(EqualsCriterion("is_active", active))

    def is_deleted(self, deleted: bool = False) -> Self:
        """Filter by deleted status.

        Args:
            deleted: Deleted status to match (default: False)

        Returns:
            Self for method chaining
        """
        return self.add_criterion(EqualsCriterion("is_deleted", deleted))

    def not_deleted(self) -> Self:
        """Filter out deleted entities.

        Returns:
            Self for method chaining
        """
        return self.is_deleted(False)

    def created_between(self, start_date: datetime | date, end_date: datetime | date) -> Self:
        """Filter by creation date range.

        Args:
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)

        Returns:
            Self for method chaining
        """
        return self.add_criterion(DateRangeCriterion("created_at", start_date, end_date))

    def created_after(self, after_date: datetime | date) -> Self:
        """Filter by creation date (after).

        Args:
            after_date: Date to compare against (exclusive)

        Returns:
            Self for method chaining
        """
        return self.add_criterion(OnOrAfterCriterion("created_at", after_date))

    def created_before(self, before_date: datetime | date) -> Self:
        """Filter by creation date (before).

        Args:
            before_date: Date to compare against (exclusive)

        Returns:
            Self for method chaining
        """
        return self.add_criterion(OnOrBeforeCriterion("created_at", before_date))

    def created_in_last_days(self, days: int) -> Self:
        """Filter by creation date within the last N days.

        Args:
            days: Number of days to look back

        Returns:
            Self for method chaining
        """
        return self.add_criterion(LastNDaysCriterion("created_at", days))

    def created_in_month(self, year: int, month: int) -> Self:
        """Filter by creation date in a specific month.

        Args:
            year: Year
            month: Month (1-12)

        Returns:
            Self for method chaining
        """
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(microseconds=1)
        else:
            end_date = datetime(year, month + 1, 1) - timedelta(microseconds=1)
        return self.created_between(start_date, end_date)

    def updated_between(self, start_date: datetime | date, end_date: datetime | date) -> Self:
        """Filter by update date range.

        Args:
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)

        Returns:
            Self for method chaining
        """
        return self.add_criterion(DateRangeCriterion("updated_at", start_date, end_date))

    def updated_after(self, after_date: datetime | date) -> Self:
        """Filter by update date (after).

        Args:
            after_date: Date to compare against (exclusive)

        Returns:
            Self for method chaining
        """
        return self.add_criterion(OnOrAfterCriterion("updated_at", after_date))

    def updated_in_last_days(self, days: int) -> Self:
        """Filter by update date within the last N days.

        Args:
            days: Number of days to look back

        Returns:
            Self for method chaining
        """
        return self.add_criterion(LastNDaysCriterion("updated_at", days))

    def by_tenant(self, tenant_id: str) -> Self:
        """Filter by tenant ID.

        Args:
            tenant_id: Tenant ID to match

        Returns:
            Self for method chaining
        """
        return self.add_criterion(EqualsCriterion("tenant_id", str(tenant_id)))

    def by_created_by(self, user_id: str) -> Self:
        """Filter by creator user ID.

        Args:
            user_id: User ID to match

        Returns:
            Self for method chaining
        """
        return self.add_criterion(EqualsCriterion("created_by", str(user_id)))

    def by_updated_by(self, user_id: str) -> Self:
        """Filter by updater user ID.

        Args:
            user_id: User ID to match

        Returns:
            Self for method chaining
        """
        return self.add_criterion(EqualsCriterion("updated_by", str(user_id)))
