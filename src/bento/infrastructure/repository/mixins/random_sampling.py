"""Random Sampling Mixin for RepositoryAdapter.

Provides random sampling operations at the Aggregate Root level.
"""

from __future__ import annotations

from typing import Any


class RandomSamplingMixin:
    """Mixin providing random sampling operations for RepositoryAdapter."""


    # Type hints for attributes provided by RepositoryAdapter
    _repository: Any  # BaseRepository instance
    _mapper: Any  # Mapper instance

    def _convert_spec_to_po(self, spec: Any) -> Any:  # type: ignore
        """Convert AR spec to PO spec (provided by RepositoryAdapter)."""
        ...

    async def find_random(self, spec: Any | None = None) -> Any | None:
        """Find one random aggregate."""
        po_spec = self._convert_spec_to_po(spec) if spec else None  # type: ignore
        po = await self._repository.find_random_po(po_spec)  # type: ignore
        if po is None:
            return None
        return self._mapper.map_reverse(po)  # type: ignore

    async def find_random_n(self, n: int, spec: Any | None = None) -> list[Any]:
        """Find N random aggregates."""
        po_spec = self._convert_spec_to_po(spec) if spec else None  # type: ignore
        pos = await self._repository.find_random_n_po(n, po_spec)  # type: ignore
        return self._mapper.map_reverse_list(pos)  # type: ignore

    async def sample_percentage(
        self, percentage: float, spec: Any | None = None, max_count: int | None = None
    ) -> list[Any]:
        """Sample a percentage of aggregates randomly."""
        po_spec = self._convert_spec_to_po(spec) if spec else None  # type: ignore
        pos = await self._repository.sample_percentage_po(  # type: ignore
            percentage, po_spec, max_count
        )
        return self._mapper.map_reverse_list(pos)  # type: ignore
