"""Soft Delete Enhanced Mixin for RepositoryAdapter.

Provides enhanced soft delete query operations at the Aggregate Root level.
"""

from __future__ import annotations

from typing import Any


class SoftDeleteEnhancedMixin:
    """Mixin providing enhanced soft delete operations for RepositoryAdapter."""

    # Type hints for attributes provided by RepositoryAdapter
    _repository: Any  # BaseRepository instance
    _mapper: Any  # Mapper instance

    def _convert_spec_to_po(self, spec: Any) -> Any:  # type: ignore
        """Convert AR spec to PO spec (provided by RepositoryAdapter)."""
        ...

    async def find_trashed(self, spec: Any | None = None) -> list[Any]:
        """Find soft-deleted aggregates."""
        po_spec = self._convert_spec_to_po(spec) if spec else None  # type: ignore
        pos = await self._repository.find_trashed_po(po_spec)  # type: ignore
        return self._mapper.map_reverse_list(pos)  # type: ignore

    async def find_with_trashed(self, spec: Any | None = None) -> list[Any]:
        """Find all aggregates including soft-deleted ones."""
        po_spec = self._convert_spec_to_po(spec) if spec else None  # type: ignore
        pos = await self._repository.find_with_trashed_po(po_spec)  # type: ignore
        return self._mapper.map_reverse_list(pos)  # type: ignore

    async def count_trashed(self, spec: Any | None = None) -> int:
        """Count soft-deleted aggregates."""
        po_spec = self._convert_spec_to_po(spec) if spec else None  # type: ignore
        return await self._repository.count_trashed_po(po_spec)  # type: ignore

    async def is_trashed(self, id: Any) -> bool:
        """Check if an aggregate is soft-deleted."""
        return await self._repository.is_trashed_po(id)  # type: ignore
