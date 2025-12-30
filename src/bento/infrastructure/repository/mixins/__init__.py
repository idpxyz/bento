"""Repository Adapter Mixins for enhanced functionality.

This package provides modular mixins for RepositoryAdapter that add
various capabilities at the Aggregate Root level.

P0 (High Priority - Completed):
- BatchOperationsMixin: Batch ID operations
- UniquenessChecksMixin: Uniqueness validation and field queries

P1 (High Priority - Completed):
- AggregateQueryMixin: Sum, avg, min, max operations
- SortingLimitingMixin: Sorting and pagination
- ConditionalUpdateMixin: Bulk update/delete by specification

P2 (Medium Priority - Completed):
- GroupByQueryMixin: Group by and aggregation
- SoftDeleteEnhancedMixin: Enhanced soft delete queries

P3 (Low Priority - Completed):
- RandomSamplingMixin: Random sampling and percentage sampling

Future:
- RelationLoadingMixin (if needed)
"""

from .aggregate_queries import AggregateQueryMixin
from .batch_operations import BatchOperationsMixin
from .conditional_updates import ConditionalUpdateMixin
from .group_by_queries import GroupByQueryMixin
from .random_sampling import RandomSamplingMixin
from .soft_delete_enhanced import SoftDeleteEnhancedMixin
from .sorting_limiting import SortingLimitingMixin
from .tenant_filter import TenantFilterMixin
from .uniqueness_checks import UniquenessChecksMixin

__all__ = [
    # P0 Mixins
    "BatchOperationsMixin",
    "UniquenessChecksMixin",
    # P1 Mixins
    "AggregateQueryMixin",
    "SortingLimitingMixin",
    "ConditionalUpdateMixin",
    # P2 Mixins
    "GroupByQueryMixin",
    "SoftDeleteEnhancedMixin",
    # P3 Mixins
    "RandomSamplingMixin",
    # Multi-tenant
    "TenantFilterMixin",
]
