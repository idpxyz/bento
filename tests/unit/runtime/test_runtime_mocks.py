"""Tests for runtime testing mocks utilities."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from bento.runtime.testing.mocks import (
    MockHandler,
    MockHandlerFactory,
    MockRepository,
    MockRepositoryFactory,
    MockService,
    MockServiceFactory,
)


@dataclass
class DummyAggregate:
    id: str
    value: str


@pytest.mark.asyncio
async def test_mock_repository_crud_operations() -> None:
    repo = MockRepository()

    saved = await repo.save(DummyAggregate(id="1", value="alpha"))
    assert saved.value == "alpha"

    fetched = await repo.get("1")
    assert fetched == saved

    assert await repo.count() == 1
    assert len(await repo.list()) == 1

    await repo.delete("1")
    assert await repo.count() == 0

    await repo.save(DummyAggregate(id="2", value="beta"))
    repo.clear()
    assert await repo.count() == 0


@pytest.mark.asyncio
async def test_mock_handler_records_calls_and_execute_flow() -> None:
    handler = MockHandler(return_value="ok")

    await handler.validate({"foo": "bar"})  # no-op
    result = await handler.execute({"foo": "bar"})

    assert result == "ok"
    assert handler.get_calls() == [{"foo": "bar"}]

    handler.reset()
    assert handler.get_calls() == []


@pytest.mark.asyncio
async def test_mock_service_dynamic_methods_and_reset() -> None:
    service = MockService(methods={"process": "done"})

    response = await service.process("payload", flag=True)
    assert response == "done"
    assert service.get_calls("process") == [(("payload",), {"flag": True})]

    service.reset()
    assert service.get_calls("process") == []


@pytest.mark.asyncio
async def test_mock_repository_factory_creates_populated_repo() -> None:
    repo = MockRepositoryFactory.create([DummyAggregate(id="5", value="seed")])

    assert await repo.count() == 1
    await repo.save(DummyAggregate(id="6", value="more"))
    assert await repo.count() == 2


@pytest.mark.asyncio
async def test_mock_handler_factory_creates_handlers_with_return_values() -> None:
    handler = MockHandlerFactory.create("hello")
    output = await handler.execute({"foo": 1})
    assert output == "hello"
    assert handler.get_calls() == [{"foo": 1}]


@pytest.mark.asyncio
async def test_mock_service_factory_creates_callable_methods() -> None:
    service = MockServiceFactory.create({"ping": "pong"})

    value = await service.ping(123)
    assert value == "pong"
    assert service.get_calls("ping") == [(((123,), {}))]
