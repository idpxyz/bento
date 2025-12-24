"""Infrastructure repository implementations.

This module provides repository adapters that bridge the Domain layer
and the Persistence layer.

Available adapters:
- RepositoryAdapter: Full implementation with AR ↔ PO mapping (production)
- SimpleRepositoryAdapter: Simplified for AR = PO cases (production)
- InMemoryRepository: In-memory implementation (testing/prototyping)

Cascade helpers (for complex aggregates with child entities):
- CascadeHelper: Helper class for managing cascade operations
- CascadeMixin: Mixin for adding cascade support to repositories
- CascadeConfig: Configuration for cascade relationships
"""

from .adapter import RepositoryAdapter
from .cascade_helper import CascadeConfig, CascadeHelper, CascadeMixin
from .inmemory import InMemoryRepository
from .registry import (
    clear_registry,
    get_repository_class,
    get_repository_registry,
    repository_for,
)
from .simple_adapter import SimpleRepositoryAdapter

__all__ = [
    # Adapters (with built-in tenant support via TenantFilterMixin)
    "RepositoryAdapter",
    "SimpleRepositoryAdapter",
    # Testing
    "InMemoryRepository",
    # Cascade helpers
    "CascadeHelper",
    "CascadeMixin",
    "CascadeConfig",
    # Registry (auto-discovery)
    "repository_for",
    "get_repository_registry",
    "get_repository_class",
    "clear_registry",
]
