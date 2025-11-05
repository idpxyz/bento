"""Infrastructure repository implementations.

This module provides repository adapters that bridge the Domain layer
and the Persistence layer.

Two adapters are available:
- RepositoryAdapter: Full implementation with AR ↔ PO mapping (complex scenarios)
- SimpleRepositoryAdapter: Simplified for AR = PO cases (simple scenarios)
"""

from .adapter import RepositoryAdapter
from .simple_adapter import SimpleRepositoryAdapter

__all__ = [
    "RepositoryAdapter",
    "SimpleRepositoryAdapter",
]
