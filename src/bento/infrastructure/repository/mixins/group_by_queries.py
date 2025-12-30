"""Group By Query Mixin for RepositoryAdapter.

Provides group by and aggregation operations at the Aggregate Root level.
"""

from __future__ import annotations

from typing import Any


class GroupByQueryMixin:
    """Mixin providing group by query operations for RepositoryAdapter."""

    # Type hints for attributes provided by RepositoryAdapter
    _repository: Any  # BaseRepository instance
    _mapper: Any  # Mapper instance

    def _convert_spec_to_po(self, spec: Any) -> Any:
        """Convert AR spec to PO spec (provided by RepositoryAdapter)."""
        ...

    async def group_by_field(self, field: str, spec: Any | None = None) -> dict[Any, int]:
        """Group aggregates by field and count each group."""
        po_spec = self._convert_spec_to_po(spec) if spec else None

        return await self._repository.group_by_field_po(field, po_spec)

    async def group_by_date(
        self, date_field: str, granularity: str = "day", spec: Any | None = None
    ) -> dict[str, int]:
        """Group aggregates by date and count each group."""
        po_spec = self._convert_spec_to_po(spec) if spec else None

        return await self._repository.group_by_date_po(date_field, granularity, po_spec)

    async def group_by_multiple_fields(
        self, fields: list[str], spec: Any | None = None
    ) -> dict[tuple, int]:
        """Group aggregates by multiple fields and count each group."""
        po_spec = self._convert_spec_to_po(spec) if spec else None

        return await self._repository.group_by_multiple_fields_po(fields, po_spec)
