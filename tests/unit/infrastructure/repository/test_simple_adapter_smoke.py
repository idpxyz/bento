from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from bento.infrastructure.repository.simple_adapter import SimpleRepositoryAdapter


class PO:
    def __init__(self, id: str | None):
        self.id = id


@pytest.mark.asyncio
async def test_simple_adapter_save_create_and_update_and_delete_all():
    repo = Mock(
        spec_set=[
            "get_po_by_id",
            "create_po",
            "update_po",
            "delete_po",
            "query_po_by_spec",
            "count_po_by_spec",
            "batch_po_delete",
        ]
    )
    repo.get_po_by_id = AsyncMock(return_value=PO("1"))
    repo.create_po = AsyncMock()
    repo.update_po = AsyncMock()
    repo.delete_po = AsyncMock()
    repo.query_po_by_spec = AsyncMock(return_value=[PO("1"), PO("2")])
    repo.count_po_by_spec = AsyncMock(return_value=2)
    repo.batch_po_delete = AsyncMock()

    adapter = SimpleRepositoryAdapter[PO, str](repository=repo)

    # create
    await adapter.save(PO(None))
    repo.create_po.assert_awaited()

    # update path (exists)
    await adapter.save(PO("1"))
    repo.update_po.assert_awaited()

    # list/find_all
    items = await adapter.list()  # type: ignore[arg-type]
    assert len(items) == 2

    # find_one (size=1)
    spec = Mock()
    spec.with_page = Mock(return_value=spec)
    repo.query_po_by_spec.return_value = [PO("1")]
    first = await adapter.find_one(spec)
    assert isinstance(first, PO)

    # find_page
    spec.with_page = Mock(return_value=spec)
    page = await adapter.find_page(spec, Mock(page=1, size=1))
    assert page.total == 2

    # delete_all
    await adapter.delete_all([PO("1")])
    repo.batch_po_delete.assert_awaited()


@pytest.mark.asyncio
async def test_simple_adapter_more_paths():
    # repo for various branches
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
        ]
    )
    repo.get_po_by_id = AsyncMock(return_value=PO("k1"))
    repo.create_po = AsyncMock()
    repo.update_po = AsyncMock()
    repo.delete_po = AsyncMock()
    repo.query_po_by_spec = AsyncMock(return_value=[PO("x")])
    repo.count_po_by_spec = AsyncMock(return_value=1)
    repo.batch_po_create = AsyncMock()
    repo.batch_po_delete = AsyncMock()

    adapter = SimpleRepositoryAdapter[PO, str](repository=repo)

    # repository property
    assert adapter.repository is repo

    # get delegates
    got = await adapter.get("k1")
    assert isinstance(got, PO)

    # count/exists
    assert await adapter.count(Mock()) == 1  # type: ignore[arg-type]
    assert await adapter.exists(Mock()) is True  # type: ignore[arg-type]

    # delete
    await adapter.delete(PO("z"))
    repo.delete_po.assert_awaited()

    # save_all empty and non-empty
    await adapter.save_all([])
    repo.batch_po_create.assert_not_called()
    await adapter.save_all([PO("a"), PO("b")])
    repo.batch_po_create.assert_awaited()

    # delete_all empty path
    repo.batch_po_delete.reset_mock()
    await adapter.delete_all([])
    repo.batch_po_delete.assert_not_called()

    # find_all delegates
    items = await adapter.find_all(Mock())  # type: ignore[arg-type]
    assert len(items) == 1

    # save with id but not existing -> create
    repo.get_po_by_id = AsyncMock(return_value=None)
    await adapter.save(PO("new"))
    repo.create_po.assert_awaited()

    # find_page zero total path
    repo.count_po_by_spec = AsyncMock(return_value=0)
    page = await adapter.find_page(Mock(), Mock(page=1, size=2))  # type: ignore[arg-type]
    assert page.total == 0 and page.items == []
