from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from bento.adapters.cache import CacheBackend, CacheConfig, CacheFactory, SerializerType
from bento.persistence.interceptor import (
    CacheInterceptor,
    InterceptorChain,
    InterceptorContext,
    OperationType,
)
from bento.persistence.repository.sqlalchemy.base import BaseRepository


class SimplePO:
    def __init__(self, id: str):
        self.id = id


class DummySpec:
    def to_cache_params(self) -> dict:
        return {"name": "bob", "active": True}


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


@pytest.mark.asyncio
async def test_query_by_spec_short_circuits_on_cache_hit():
    # session mock
    session = Mock(spec_set=["get", "execute", "add", "merge", "delete", "flush"])
    session.execute = AsyncMock(return_value=_FakeResult([SimplePO("1"), SimplePO("2")]))
    session.flush = AsyncMock()

    # cache + chain
    cache = await CacheFactory.create(
        CacheConfig(backend=CacheBackend.MEMORY, ttl=60, serializer=SerializerType.PICKLE)
    )
    chain = InterceptorChain([CacheInterceptor(cache, ttl=60, enabled=True)])

    repo = BaseRepository[SimplePO, str](
        session=session, po_type=SimplePO, actor="tester", interceptor_chain=chain
    )

    spec = DummySpec()

    # Pre-seed cache via interceptor batch processing to avoid constructing SA select(SimplePO)
    ctx = InterceptorContext(
        session=session,
        entity_type=SimplePO,
        operation=OperationType.QUERY,
        actor="tester",
        context_data={"query_params": spec.to_cache_params()},
    )
    seeded = [SimplePO("1"), SimplePO("2")]
    await chain.process_batch_results(ctx, seeded)

    # Now repository should short-circuit and not call DB
    session.execute.reset_mock()
    rows = await repo.query_po_by_spec(spec)
    assert isinstance(rows, list)
    assert len(rows) == 2
    session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_delete_po_triggers_invalidation_via_repo():
    session = Mock(spec_set=["get", "execute", "add", "merge", "delete", "flush"])
    session.delete = AsyncMock()
    session.flush = AsyncMock()

    cache = await CacheFactory.create(
        CacheConfig(backend=CacheBackend.MEMORY, ttl=60, serializer=SerializerType.PICKLE)
    )
    chain = InterceptorChain([CacheInterceptor(cache, ttl=60, enabled=True)])

    repo = BaseRepository[SimplePO, str](
        session=session, po_type=SimplePO, actor="tester", interceptor_chain=chain
    )

    # seed cache
    await cache.set("SimplePO:id:7", SimplePO("7"), ttl=60)
    po = SimplePO("7")

    await repo.delete_po(po)

    assert await cache.get("SimplePO:id:7") is None


@pytest.mark.asyncio
async def test_batch_po_delete_triggers_invalidation_via_repo():
    session = Mock(spec_set=["get", "execute", "add", "merge", "delete", "flush"])
    session.delete = AsyncMock()
    session.flush = AsyncMock()

    cache = await CacheFactory.create(
        CacheConfig(backend=CacheBackend.MEMORY, ttl=60, serializer=SerializerType.PICKLE)
    )
    chain = InterceptorChain([CacheInterceptor(cache, ttl=60, enabled=True)])

    repo = BaseRepository[SimplePO, str](
        session=session, po_type=SimplePO, actor="tester", interceptor_chain=chain
    )

    # seed
    await cache.set("SimplePO:id:1", SimplePO("1"), ttl=60)
    await cache.set("SimplePO:id:2", SimplePO("2"), ttl=60)
    await cache.set("SimplePO:query:flag:true", [SimplePO("1"), SimplePO("2")], ttl=60)

    pos = [SimplePO("1"), SimplePO("2")]

    await repo.batch_po_delete(pos)

    assert await cache.get("SimplePO:id:1") is None
    assert await cache.get("SimplePO:id:2") is None
    # query prefix invalidated -> miss
    # build a cache-before context
    ctx = InterceptorContext(
        session=session,
        entity_type=SimplePO,
        operation=OperationType.QUERY,
        actor="tester",
        context_data={"query_params": {"flag": True}},
    )
    assert await chain.execute_before(ctx) is None
