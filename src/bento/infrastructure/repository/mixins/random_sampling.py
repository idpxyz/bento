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

    def _convert_spec_to_po(self, spec: Any) -> Any:

        """Convert AR spec to PO spec (provided by RepositoryAdapter)."""
        ...

    async def find_random(self, spec: Any | None = None) -> Any | None:
        """Find one random aggregate."""
        po_spec = self._convert_spec_to_po(spec) if spec else None

        po = await self._repository.find_random_po(po_spec)

        if po is None:
            return None
        return self._mapper.map_reverse(po)


    async def find_random_n(self, n: int, spec: Any | None = None) -> list[Any]:
        """Find N random aggregates."""
        po_spec = self._convert_spec_to_po(spec) if spec else None

        pos = await self._repository.find_random_n_po(n, po_spec)

        return self._mapper.map_reverse_list(pos)


    async def sample_percentage(
        self, percentage: float, spec: Any | None = None, max_count: int | None = None
    ) -> list[Any]:
        """Sample a percentage of aggregates randomly."""
        po_spec = self._convert_spec_to_po(spec) if spec else None

        pos = await self._repository.sample_percentage_po(

            percentage, po_spec, max_count
        )
        return self._mapper.map_reverse_list(pos)

