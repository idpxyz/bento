from __future__ import annotations

from unittest.mock import Mock

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
async def test_query_without_params_is_not_cached():
    cache = await CacheFactory.create(
        CacheConfig(backend=CacheBackend.MEMORY, ttl=60, serializer=SerializerType.PICKLE)
    )
    chain = InterceptorChain([CacheInterceptor(cache, ttl=60, enabled=True)])

    # No query_params
    ctx = InterceptorContext(
        session=Mock(),
        entity_type=SimplePO,
        operation=OperationType.QUERY,
        actor="tester",
        context_data={},
    )

    # miss (no params)
    miss = await chain.execute_before(ctx)
    assert miss is None

    # process results should NOT write cache because no key derived
    results = [SimplePO("1"), SimplePO("2")]
    await chain.process_batch_results(ctx, results)

    # still miss
    miss2 = await chain.execute_before(ctx)
    assert miss2 is None


@pytest.mark.asyncio
async def test_get_by_entity_id_when_context_has_no_entity_id():
    cache = await CacheFactory.create(
        CacheConfig(backend=CacheBackend.MEMORY, ttl=60, serializer=SerializerType.PICKLE)
    )
    chain = InterceptorChain([CacheInterceptor(cache, ttl=60, enabled=True)])

    entity = SimplePO("5")
    ctx = InterceptorContext(
        session=Mock(),
        entity_type=SimplePO,
        operation=OperationType.READ,
        entity=entity,
        actor="tester",
        context_data={},
    )

    # write via process_result (simulate downstream result)
    await chain.process_result(ctx, entity)

    # now before_operation with same context should hit by entity.id
    hit = await chain.execute_before(ctx)
    assert isinstance(hit, SimplePO) and hit.id == "5"


@pytest.mark.asyncio
async def test_cache_interceptor_disabled_no_effect():
    cache = await CacheFactory.create(
        CacheConfig(backend=CacheBackend.MEMORY, ttl=60, serializer=SerializerType.PICKLE)
    )
    chain = InterceptorChain([CacheInterceptor(cache, ttl=60, enabled=False)])

    entity = SimplePO("6")
    ctx = InterceptorContext(
        session=Mock(),
        entity_type=SimplePO,
        operation=OperationType.GET,
        actor="tester",
        context_data={"entity_id": "6"},
    )

    # disabled -> miss
    assert await chain.execute_before(ctx) is None

    # process_result should not write
    await chain.process_result(ctx, entity)
    assert await chain.execute_before(ctx) is None


@pytest.mark.asyncio
async def test_batch_update_invalidates_ids_and_query_prefix():
    cache = await CacheFactory.create(
        CacheConfig(backend=CacheBackend.MEMORY, ttl=60, serializer=SerializerType.PICKLE)
    )
    chain = InterceptorChain([CacheInterceptor(cache, ttl=60, enabled=True)])

    et = "SimplePO"
    await cache.set(f"{et}:id:1", SimplePO("1"), ttl=60)
    await cache.set(f"{et}:id:2", SimplePO("2"), ttl=60)
    await cache.set(f"{et}:query:name:alice", [SimplePO("1"), SimplePO("2")], ttl=60)

    entities = [SimplePO("1"), SimplePO("2")]
    ctx = InterceptorContext(
        session=Mock(),
        entity_type=SimplePO,
        operation=OperationType.BATCH_UPDATE,
        entities=entities,
        actor="tester",
    )

    await chain.process_batch_results(ctx, entities)

    assert await cache.get(f"{et}:id:1") is None
    assert await cache.get(f"{et}:id:2") is None

    # query prefix invalidated -> miss
    qctx = InterceptorContext(
        session=Mock(),
        entity_type=SimplePO,
        operation=OperationType.QUERY,
        actor="tester",
        context_data={"query_params": {"name": "alice"}},
    )
    assert await chain.execute_before(qctx) is None


@pytest.mark.asyncio
async def test_batch_delete_invalidates_ids_and_query_prefix():
    cache = await CacheFactory.create(
        CacheConfig(backend=CacheBackend.MEMORY, ttl=60, serializer=SerializerType.PICKLE)
    )
    chain = InterceptorChain([CacheInterceptor(cache, ttl=60, enabled=True)])

    et = "SimplePO"
    await cache.set(f"{et}:id:3", SimplePO("3"), ttl=60)
    await cache.set(f"{et}:query:flag:true", [SimplePO("3")], ttl=60)

    entities = [SimplePO("3")]
    ctx = InterceptorContext(
        session=Mock(),
        entity_type=SimplePO,
        operation=OperationType.BATCH_DELETE,
        entities=entities,
        actor="tester",
    )

    await chain.process_batch_results(ctx, entities)

    assert await cache.get(f"{et}:id:3") is None
    qctx = InterceptorContext(
        session=Mock(),
        entity_type=SimplePO,
        operation=OperationType.QUERY,
        actor="tester",
        context_data={"query_params": {"flag": True}},
    )
    assert await chain.execute_before(qctx) is None


@pytest.mark.asyncio
async def test_prefix_is_applied_to_keys():
    # cache has its own prefix; interceptor adds its own prefix on top
    cache = await CacheFactory.create(
        CacheConfig(
            backend=CacheBackend.MEMORY,
            ttl=60,
            serializer=SerializerType.PICKLE,
            prefix="env:",
        )
    )
    chain = InterceptorChain([CacheInterceptor(cache, ttl=60, enabled=True, prefix="ci:")])

    entity = SimplePO("9")
    ctx = InterceptorContext(
        session=Mock(),
        entity_type=SimplePO,
        operation=OperationType.GET,
        actor="tester",
        context_data={"entity_id": "9"},
    )

    await chain.process_result(ctx, entity)

    # Expect stored under env:ci:SimplePO:id:9 (env: added by adapter, ci: by interceptor)
    # We call adapter without the env: prefix
    stored = await cache.get("ci:SimplePO:id:9")
    assert isinstance(stored, SimplePO) and stored.id == "9"
