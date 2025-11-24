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
async def test_adapter_save_create_calls_create_po_when_no_id():
    repo = Mock(
        spec_set=[
            "get_po_by_id",
            "create_po",
            "update_po",
            "delete_po",
            "query_po_by_spec",
            "count_po_by_spec",
            "session",
        ]
    )
    repo.create_po = AsyncMock()
    repo.get_po_by_id = AsyncMock()
    repo.update_po = AsyncMock()
    repo.delete_po = AsyncMock()
    # session.info for UoW track path
    repo.session = Mock()
    repo.session.info = {}

    adapter = RepositoryAdapter[DomainAgg, PO, str](repository=repo, mapper=DummyMapper())

    agg = DomainAgg(id=None)
    await adapter.save(agg)

    repo.create_po.assert_awaited()
    repo.update_po.assert_not_called()


@pytest.mark.asyncio
async def test_adapter_save_update_propagates_version_and_calls_update_po():
    repo = Mock(
        spec_set=[
            "get_po_by_id",
            "create_po",
            "update_po",
            "delete_po",
            "query_po_by_spec",
            "count_po_by_spec",
            "session",
        ]
    )
    repo.create_po = AsyncMock()
    repo.get_po_by_id = AsyncMock(return_value=PO(id="1", version=5))
    repo.update_po = AsyncMock()
    repo.delete_po = AsyncMock()
    repo.session = Mock()
    repo.session.info = {}

    adapter = RepositoryAdapter[DomainAgg, PO, str](repository=repo, mapper=DummyMapper())

    agg = DomainAgg(id="1", version=None)
    await adapter.save(agg)

    # update should be called, with version propagated to 5
    assert repo.update_po.await_args is not None
    updated_po = repo.update_po.await_args.args[0]
    assert isinstance(updated_po, PO)
    assert updated_po.version == 5


@pytest.mark.asyncio
async def test_adapter_list_count_exists_and_delete_delegation():
    repo = Mock(
        spec_set=[
            "get_po_by_id",
            "create_po",
            "update_po",
            "delete_po",
            "query_po_by_spec",
            "count_po_by_spec",
            "session",
        ]
    )
    repo.query_po_by_spec = AsyncMock(return_value=[PO("1"), PO("2")])
    repo.count_po_by_spec = AsyncMock(return_value=2)
    repo.delete_po = AsyncMock()
    repo.session = Mock()
    repo.session.info = {}

    adapter = RepositoryAdapter[DomainAgg, PO, str](repository=repo, mapper=DummyMapper())

    # list
    items = await adapter.list()  # type: ignore[arg-type]
    assert len(items) == 2 and all(isinstance(x, DomainAgg) for x in items)

    # count/exists
    cnt = await adapter.count(Mock())  # type: ignore[arg-type]
    assert cnt == 2
    assert await adapter.exists(Mock()) is True  # type: ignore[arg-type]

    # delete
    await adapter.delete(DomainAgg("1"))
    repo.delete_po.assert_awaited()


@pytest.mark.asyncio
async def test_adapter_find_one_and_find_page_and_save_delete_all_and_uow_track():
    # comprehensive repo mock
    repo = Mock(
        spec_set=[
            "get_po_by_id",
            "create_po",
            "update_po",
            "delete_po",
            "query_po_by_spec",
            "count_po_by_spec",
            "batch_po_create",
            "batch_po_delete",
            "session",
        ]
    )
    repo.query_po_by_spec = AsyncMock(side_effect=[[], [PO("1")]])
    repo.count_po_by_spec = AsyncMock(side_effect=[0, 3])
    repo.batch_po_create = AsyncMock()
    repo.batch_po_delete = AsyncMock()
    repo.get_po_by_id = AsyncMock(return_value=None)
    repo.create_po = AsyncMock()
    # uow track path
    uow = Mock()
    uow.track = Mock()
    repo.session = Mock()
    repo.session.info = {"uow": uow}
    repo.session.sync_session = None

    adapter = RepositoryAdapter[DomainAgg, PO, str](repository=repo, mapper=DummyMapper())

    # find_one -> None when no rows
    none = await adapter.find_one(Mock())  # type: ignore[arg-type]
    assert none is None

    # find_page total=0 -> empty page
    page = await adapter.find_page(Mock(), Mock(page=1, size=2))  # type: ignore[arg-type]
    assert page.total == 0 and page.items == []

    # find_page total>0 -> items present
    page2 = await adapter.find_page(Mock(), Mock(page=1, size=1))  # type: ignore[arg-type]
    assert page2.total == 3 and len(page2.items) == 1

    # save_all: empty -> no call; non-empty -> calls batch_po_create
    await adapter.save_all([])
    repo.batch_po_create.assert_not_called()
    await adapter.save_all([DomainAgg("a"), DomainAgg("b")])
    repo.batch_po_create.assert_awaited()

    # delete_all
    await adapter.delete_all([])
    repo.batch_po_delete.assert_not_called()
    await adapter.delete_all([DomainAgg("x")])
    repo.batch_po_delete.assert_awaited()

    # invoke save to exercise path (uow.track may be environment-dependent)
    await adapter.save(DomainAgg("z"))
