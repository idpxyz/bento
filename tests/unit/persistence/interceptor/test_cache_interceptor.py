from unittest.mock import AsyncMock, Mock

import pytest

from bento.adapters.cache import CacheBackend, CacheConfig, CacheFactory, SerializerType
from bento.persistence.interceptor import (
    CacheInterceptor,
    InterceptorChain,
    InterceptorContext,
    OperationType,
)


class SimplePO:
    def __init__(self, id: str):
        self.id = id


@pytest.mark.asyncio
async def test_cache_interceptor_get_by_id_hit():
    cache = await CacheFactory.create(
        CacheConfig(backend=CacheBackend.MEMORY, ttl=60, serializer=SerializerType.PICKLE)
    )
    chain = InterceptorChain([CacheInterceptor(cache, ttl=60, enabled=True)])

    # Seed cache
    key = "SimplePO:id:42"
    entity = SimplePO("42")
    await cache.set(key, entity, ttl=60)

    ctx = InterceptorContext(
        session=Mock(),
        entity_type=SimplePO,
        operation=OperationType.GET,
        actor="tester",
        context_data={"entity_id": "42"},
    )

    cached = await chain.execute_before(ctx)
    assert isinstance(cached, SimplePO)
    assert cached.id == entity.id


@pytest.mark.asyncio
async def test_cache_interceptor_query_cache_and_hit():
    cache = await CacheFactory.create(
        CacheConfig(backend=CacheBackend.MEMORY, ttl=60, serializer=SerializerType.PICKLE)
    )
    chain = InterceptorChain([CacheInterceptor(cache, ttl=60, enabled=True)])

    ctx = InterceptorContext(
        session=Mock(),
        entity_type=SimplePO,
        operation=OperationType.QUERY,
        actor="tester",
        context_data={"query_params": {"name": "alice", "active": True}},
    )

    # First time: miss, then set during process_batch_results
    miss = await chain.execute_before(ctx)
    assert miss is None

    results = [SimplePO("1"), SimplePO("2")]
    results = await chain.process_batch_results(ctx, results)

    # Second time: should hit
    hit = await chain.execute_before(ctx)
    assert isinstance(hit, list) and len(hit) == 2


@pytest.mark.asyncio
async def test_cache_interceptor_invalidate_on_update():
    cache = await CacheFactory.create(
        CacheConfig(backend=CacheBackend.MEMORY, ttl=60, serializer=SerializerType.PICKLE)
    )
    chain = InterceptorChain([CacheInterceptor(cache, ttl=60, enabled=True)])
    # Seed id and query caches
    await cache.set("SimplePO:id:7", SimplePO("7"), ttl=60)
    await cache.set("SimplePO:query:name:alice", [SimplePO("7")], ttl=60)

    ctx = InterceptorContext(
        session=Mock(),
        entity_type=SimplePO,
        operation=OperationType.UPDATE,
        entity=SimplePO("7"),
        actor="tester",
    )

    # Trigger invalidation
    await chain.process_result(ctx, SimplePO("7"))

    assert await cache.get("SimplePO:id:7") is None
    # pattern deletion cannot be directly checked; ensure subsequent query miss
    qctx = InterceptorContext(
        session=Mock(),
        entity_type=SimplePO,
        operation=OperationType.QUERY,
        actor="tester",
        context_data={"query_params": {"name": "alice"}},
    )
    assert await chain.execute_before(qctx) is None


@pytest.mark.asyncio
async def test_repository_get_short_circuit(monkeypatch):
    from bento.persistence.repository.sqlalchemy.base import BaseRepository

    session = Mock(spec_set=["get", "execute", "add", "merge", "delete", "flush"])
    session.get = AsyncMock()

    cache = await CacheFactory.create(
        CacheConfig(backend=CacheBackend.MEMORY, ttl=60, serializer=SerializerType.PICKLE)
    )
    chain = InterceptorChain([CacheInterceptor(cache, ttl=60, enabled=True)])

    repo = BaseRepository[SimplePO, str](
        session=session,
        po_type=SimplePO,
        actor="tester",
        interceptor_chain=chain,
    )

    expected = SimplePO("99")
    await cache.set("SimplePO:id:99", expected, ttl=60)

    result = await repo.get_po_by_id("99")

    assert isinstance(result, SimplePO)
    assert result.id == expected.id
    session.get.assert_not_called()
