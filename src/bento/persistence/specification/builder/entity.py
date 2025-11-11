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
    IsNotNullCriterion,
    IsNullCriterion,
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
    - Soft delete queries (deleted_at timestamp)
    - Tenant queries

    Soft Delete Pattern:
        By default, this builder AUTOMATICALLY filters out soft-deleted records
        (WHERE deleted_at IS NULL). This is a safety feature to prevent
        accidentally querying deleted data.

        To include soft-deleted records, explicitly call .include_deleted().
        To query ONLY soft-deleted records, call .include_deleted().only_deleted().

    Example:
        ```python
        # Default: excludes soft-deleted records
        spec = EntitySpecificationBuilder().is_active().build()
        # WHERE is_active = true AND deleted_at IS NULL

        # Include soft-deleted records
        spec = EntitySpecificationBuilder().is_active().include_deleted().build()
        # WHERE is_active = true

        # Query only soft-deleted records
        spec = EntitySpecificationBuilder().include_deleted().only_deleted().build()
        # WHERE deleted_at IS NOT NULL
        ```
    """

    def __init__(self):
        """Initialize builder with default soft delete filter.

        By default, filters out soft-deleted records (deleted_at IS NULL).
        This is a safety feature following the "secure by default" principle.
        """
        super().__init__()
        # Default: exclude soft-deleted records (secure by default)
        self._criteria.append(IsNullCriterion("deleted_at"))

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

    def include_deleted(self) -> Self:
        """Include soft-deleted entities in the query.

        Removes the default deleted_at IS NULL filter.
        Use this when you need to query both deleted and non-deleted records.

        Returns:
            Self for method chaining

        Example:
            ```python
            # Query all records (including soft-deleted)
            spec = EntitySpecificationBuilder().include_deleted().build()
            # WHERE ... (no deleted_at filter)
            ```
        """
        # Remove all deleted_at IS NULL criteria
        self._criteria = [
            c
            for c in self._criteria
            if not (isinstance(c, IsNullCriterion) and c.to_filter().field == "deleted_at")
        ]
        return self

    def only_deleted(self) -> Self:
        """Query only soft-deleted entities.

        This method should be called AFTER include_deleted() to first remove
        the default filter, then add the IS NOT NULL filter.

        Returns:
            Self for method chaining

        Example:
            ```python
            # Query only soft-deleted records
            spec = EntitySpecificationBuilder().include_deleted().only_deleted().build()
            # WHERE deleted_at IS NOT NULL
            ```
        """
        return self.add_criterion(IsNotNullCriterion("deleted_at"))

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
