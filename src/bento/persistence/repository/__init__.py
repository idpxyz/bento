"""Repository implementations for Bento Framework.

This module contains Persistence-layer repository implementations
that operate on Persistence Objects (PO).

For Domain-layer repository adapters (operating on Aggregate Roots),
see bento.infrastructure.repository.
"""

from .sqlalchemy import BaseRepository

__all__ = ["BaseRepository"]
