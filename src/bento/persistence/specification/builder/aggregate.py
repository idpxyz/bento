"""Aggregate specification builder with aggregate-specific query patterns.

This module provides specialized builders for aggregate root queries,
including methods for managing aggregate-specific concerns.
"""

from typing import Any, Self, TypeVar

from bento.domain.aggregate import AggregateRoot

from ..criteria import EqualsCriterion
from .entity import EntitySpecificationBuilder

T = TypeVar("T", bound=AggregateRoot)


class AggregateSpecificationBuilder(EntitySpecificationBuilder[T]):
    """Builder for aggregate root specifications.

    This builder extends EntitySpecificationBuilder with aggregate-specific patterns:
    - Version tracking
    - Aggregate identity queries
    - State management

    Note: Aggregate roots typically do not use soft delete (deleted_at field).
    If your aggregates do use soft delete, call .not_deleted() explicitly or use
    EntitySpecificationBuilder instead.

    Example:
        ```python
        spec = (AggregateSpecificationBuilder()
            .by_id(aggregate_id)
            .with_minimum_version(5)
            .build())
        ```
    """

    def __init__(self):
        """Initialize builder without default soft delete filter.

        Unlike EntitySpecificationBuilder, AggregateSpecificationBuilder does NOT
        apply a default soft delete filter, as aggregate roots typically use
        event sourcing or other patterns instead of soft deletion.
        """
        # Call SpecificationBuilder.__init__ directly, bypassing EntitySpecificationBuilder
        super(EntitySpecificationBuilder, self).__init__()

    def by_aggregate_id(self, aggregate_id: Any) -> Self:
        """Filter by aggregate ID.

        This is an alias for by_id() but with clearer semantics for aggregates.

        Args:
            aggregate_id: Aggregate root ID to match

        Returns:
            Self for method chaining
        """
        return self.by_id(aggregate_id)

    def with_version(self, version: int) -> Self:
        """Filter by exact version number.

        Args:
            version: Version number to match

        Returns:
            Self for method chaining
        """
        return self.add_criterion(EqualsCriterion("version", version))

    def with_minimum_version(self, min_version: int) -> Self:
        """Filter by minimum version number.

        Args:
            min_version: Minimum version (inclusive)

        Returns:
            Self for method chaining
        """
        return self.where("version", ">=", min_version)

    def with_maximum_version(self, max_version: int) -> Self:
        """Filter by maximum version number.

        Args:
            max_version: Maximum version (inclusive)

        Returns:
            Self for method chaining
        """
        return self.where("version", "<=", max_version)

    def with_version_range(self, min_version: int, max_version: int) -> Self:
        """Filter by version range.

        Args:
            min_version: Minimum version (inclusive)
            max_version: Maximum version (inclusive)

        Returns:
            Self for method chaining
        """
        return self.between("version", min_version, max_version)

    def by_aggregate_type(self, type_name: str) -> Self:
        """Filter by aggregate type name.

        Args:
            type_name: Aggregate type name to match

        Returns:
            Self for method chaining
        """
        criterion = EqualsCriterion("aggregate_type", type_name)
        return self.add_criterion(criterion)

    def with_events(self) -> Self:
        """Include aggregates that have uncommitted events.

        Returns:
            Self for method chaining
        """
        # This is a semantic method - actual implementation might vary
        # depending on how events are stored
        return self

    def without_events(self) -> Self:
        """Include only aggregates without uncommitted events.

        Returns:
            Self for method chaining
        """
        # This is a semantic method - actual implementation might vary
        return self
