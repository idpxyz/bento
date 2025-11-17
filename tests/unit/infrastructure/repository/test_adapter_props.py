from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from bento.application.ports.mapper import Mapper
from bento.infrastructure.repository.adapter import RepositoryAdapter


class DomainAgg:
    def __init__(self, id: str | None):
        self.id = id


class PO:
    def __init__(self, id: str | None):
        self.id = id


class DummyMapper(Mapper[DomainAgg, PO]):
    def map(self, domain: DomainAgg) -> PO:
        return PO(domain.id)

    def map_reverse(self, po: PO) -> DomainAgg:
        return DomainAgg(po.id)

    def map_list(self, domains: list[DomainAgg]) -> list[PO]:
        return [self.map(d) for d in domains]

    def map_reverse_list(self, pos: list[PO]) -> list[DomainAgg]:
        return [self.map_reverse(p) for p in pos]


@pytest.mark.asyncio
async def test_repository_adapter_properties():
    repo = Mock(spec_set=["get_po_by_id", "create_po", "update_po", "session"])
    repo.get_po_by_id = AsyncMock(return_value=None)
    repo.create_po = AsyncMock()
    repo.update_po = AsyncMock()
    repo.session = Mock()
    repo.session.info = {}

    mapper = DummyMapper()
    adapter = RepositoryAdapter[DomainAgg, PO, str](repository=repo, mapper=mapper)

    assert adapter.repository is repo
    assert adapter.mapper is mapper
