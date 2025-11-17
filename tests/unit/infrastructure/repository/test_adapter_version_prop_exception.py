from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from bento.application.ports.mapper import Mapper
from bento.infrastructure.repository.adapter import RepositoryAdapter


class DomainAgg:
    def __init__(self, id: str | None, version: int | None = None):
        self.id = id
        self.version = version


class Existing:
    def __init__(self, version: int | None):
        self.version = version


class POReadOnly:
    def __init__(self, id: str | None):
        self._id = id
        self._version = None

    @property
    def id(self) -> str | None:  # type: ignore[override]
        return self._id

    @property
    def version(self) -> int | None:  # type: ignore[override]
        return self._version


class DummyMapper(Mapper[DomainAgg, POReadOnly]):
    def map(self, domain: DomainAgg) -> POReadOnly:
        return POReadOnly(domain.id)

    def map_reverse(self, po: POReadOnly) -> DomainAgg:
        return DomainAgg(po.id, po.version)

    def map_list(self, domains: list[DomainAgg]) -> list[POReadOnly]:
        return [self.map(d) for d in domains]

    def map_reverse_list(self, pos: list[POReadOnly]) -> list[DomainAgg]:
        return [self.map_reverse(p) for p in pos]


@pytest.mark.asyncio
async def test_version_propagation_swallow_exception_on_readonly_property():
    repo = Mock(spec_set=["get_po_by_id", "create_po", "update_po", "session"])
    repo.get_po_by_id = AsyncMock(return_value=Existing(7))
    repo.create_po = AsyncMock()
    repo.update_po = AsyncMock()
    repo.session = Mock()
    repo.session.info = {}

    adapter = RepositoryAdapter[DomainAgg, POReadOnly, str](repository=repo, mapper=DummyMapper())

    # Should not raise even though version assignment will fail (readonly property)
    await adapter.save(DomainAgg("1", version=None))

    # Update path still reached
    repo.update_po.assert_awaited()
