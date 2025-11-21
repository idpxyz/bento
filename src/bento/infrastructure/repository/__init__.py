"""Infrastructure repository implementations.

This module provides repository adapters that bridge the Domain layer
and the Persistence layer.

Available adapters:
- RepositoryAdapter: Full implementation with AR ↔ PO mapping (complex scenarios)
- SimpleRepositoryAdapter: Simplified for AR = PO cases (simple scenarios)

Cascade helpers (for complex aggregates with child entities):
- CascadeHelper: Helper class for managing cascade operations
- CascadeMixin: Mixin for adding cascade support to repositories
- CascadeConfig: Configuration for cascade relationships
"""

from .adapter import RepositoryAdapter
from .cascade_helper import CascadeConfig, CascadeHelper, CascadeMixin
from .simple_adapter import SimpleRepositoryAdapter

__all__ = [
    "RepositoryAdapter",
    "SimpleRepositoryAdapter",
    "CascadeHelper",
    "CascadeMixin",
    "CascadeConfig",
]
