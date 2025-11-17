from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from bento.application.ports.mapper import Mapper
from bento.infrastructure.repository.adapter import RepositoryAdapter


class DomainAgg:
    def __init__(self, id: str | None, version: int | None = None):
        self.id = id
        self.version = version


class PO:
    def __init__(self, id: str | None, version: int | None = None):
        self.id = id
        self.version = version


class DummyMapper(Mapper[DomainAgg, PO]):
    def map(self, domain: DomainAgg) -> PO:
        # produce a PO with no version to trigger propagation
        return PO(domain.id, domain.version)

    def map_reverse(self, po: PO) -> DomainAgg:
        return DomainAgg(po.id, po.version)

    def map_list(self, domains: list[DomainAgg]) -> list[PO]:
        return [self.map(d) for d in domains]

    def map_reverse_list(self, pos: list[PO]) -> list[DomainAgg]:
        return [self.map_reverse(p) for p in pos]


@pytest.mark.asyncio
async def test_version_is_propagated_on_update_path():
    # existing has version=7; transient PO has None -> should be set to 7
    repo = Mock(spec_set=["get_po_by_id", "create_po", "update_po", "session"])
    repo.get_po_by_id = AsyncMock(return_value=PO("1", version=7))
    repo.create_po = AsyncMock()
    repo.update_po = AsyncMock()
    repo.session = Mock()
    repo.session.info = {}

    adapter = RepositoryAdapter[DomainAgg, PO, str](repository=repo, mapper=DummyMapper())

    await adapter.save(DomainAgg("1", version=None))

    # ensure update called with a PO whose version was propagated to 7
    assert repo.update_po.await_count == 1
    args, kwargs = repo.update_po.await_args  # type: ignore[attr-defined]
    sent_po: PO = args[0]
    assert isinstance(sent_po, PO)
    assert sent_po.version == 7
