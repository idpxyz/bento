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
        return PO(domain.id, domain.version)

    def map_reverse(self, po: PO) -> DomainAgg:
        return DomainAgg(po.id, po.version)

    def map_list(self, domains: list[DomainAgg]) -> list[PO]:
        return [self.map(d) for d in domains]

    def map_reverse_list(self, pos: list[PO]) -> list[DomainAgg]:
        return [self.map_reverse(p) for p in pos]


@pytest.mark.asyncio
async def test_get_none_and_get_maps_when_found():
    repo = Mock(spec_set=["get_po_by_id", "query_po_by_spec", "count_po_by_spec", "session"])
    repo.get_po_by_id = AsyncMock(side_effect=[None, PO("1")])
    repo.session = Mock()
    repo.session.info = {}

    adapter = RepositoryAdapter[DomainAgg, PO, str](repository=repo, mapper=DummyMapper())

    # none path
    assert await adapter.get("1") is None

    # found path -> mapped
    ent = await adapter.get("1")
    assert isinstance(ent, DomainAgg) and ent.id == "1"


@pytest.mark.asyncio
async def test_find_one_success_and_find_all_by_spec():
    repo = Mock(spec_set=["query_po_by_spec", "count_po_by_spec", "session"])
    repo.query_po_by_spec = AsyncMock(side_effect=[[PO("2")], [PO("2"), PO("3")]])
    repo.count_po_by_spec = AsyncMock(return_value=2)
    repo.session = Mock()
    repo.session.info = {}

    adapter = RepositoryAdapter[DomainAgg, PO, str](repository=repo, mapper=DummyMapper())

    # find_one success
    one = await adapter.find_one(Mock())  # type: ignore[arg-type]
    assert isinstance(one, DomainAgg) and one.id == "2"

    # find_all delegates to list(spec)
    all_items = await adapter.find_all(Mock())  # type: ignore[arg-type]
    assert len(all_items) == 2 and all(isinstance(x, DomainAgg) for x in all_items)


@pytest.mark.asyncio
async def test_adapter_mapper_property_and_uow_swallow_exception():
    # repo without session attribute to trigger swallow path
    repo = Mock(spec_set=["get_po_by_id", "create_po", "update_po"])
    repo.get_po_by_id = AsyncMock(return_value=PO("1"))
    repo.create_po = AsyncMock()
    repo.update_po = AsyncMock()

    mapper = DummyMapper()
    adapter = RepositoryAdapter[DomainAgg, PO, str](repository=repo, mapper=mapper)

    # mapper property
    assert adapter.mapper is mapper

    # save should not raise even though repo lacks session (swallowed)
    await adapter.save(DomainAgg("1"))
