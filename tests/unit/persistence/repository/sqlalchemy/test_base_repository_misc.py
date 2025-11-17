from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from bento.persistence.interceptor import InterceptorChain
from bento.persistence.repository.sqlalchemy.base import BaseRepository
from bento.persistence.specification import CompositeSpecification


class Base(DeclarativeBase):
    pass


class Model(Base):
    __tablename__ = "t_model"
    id: Mapped[str] = mapped_column(String, primary_key=True)


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    class _Scalars:
        def __init__(self, rows):
            self._rows = rows

        def all(self):
            return self._rows

    def scalars(self):
        return _FakeResult._Scalars(self._rows)


class DummySpec(CompositeSpecification[Model]):
    # No to_cache_params on purpose
    def to_sqlalchemy(self):  # pragma: no cover - not used
        return None


@pytest.mark.asyncio
async def test_get_po_by_id_without_chain():
    session = Mock(spec_set=["get", "execute", "add", "merge", "delete", "flush"])
    session.get = AsyncMock(return_value=Model(id="1"))

    repo = BaseRepository[Model, str](session=session, po_type=Model, actor="tester")

    po = await repo.get_po_by_id("1")
    assert isinstance(po, Model)
    session.get.assert_awaited()


@pytest.mark.asyncio
async def test_query_po_by_spec_without_chain():
    session = Mock(spec_set=["get", "execute", "add", "merge", "delete", "flush"])
    session.execute = AsyncMock(return_value=_FakeResult([Model(id="1"), Model(id="2")]))

    repo = BaseRepository[Model, str](session=session, po_type=Model, actor="tester")

    rows = await repo.query_po_by_spec(DummySpec())
    assert isinstance(rows, list) and len(rows) == 2
    session.execute.assert_awaited()


@pytest.mark.asyncio
async def test_query_po_by_spec_with_empty_chain_and_no_cache_params():
    session = Mock(spec_set=["get", "execute", "add", "merge", "delete", "flush"])
    session.execute = AsyncMock(return_value=_FakeResult([Model(id="1")]))

    chain = InterceptorChain([])
    repo = BaseRepository[Model, str](
        session=session, po_type=Model, actor="tester", interceptor_chain=chain
    )

    rows = await repo.query_po_by_spec(DummySpec())
    assert isinstance(rows, list) and len(rows) == 1
    session.execute.assert_awaited()
