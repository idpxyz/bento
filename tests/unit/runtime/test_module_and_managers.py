"""Unit tests for Bento runtime module base class and managers."""

from __future__ import annotations

import sys
from types import ModuleType
from typing import TYPE_CHECKING, cast

import pytest

from bento.runtime.container import BentoContainer
from bento.runtime.messaging.manager import MessagingManager
from bento.runtime.module import BentoModule

if TYPE_CHECKING:
    from bento.runtime.bootstrap import BentoRuntime


class SampleModule(BentoModule):
    """Concrete module used for tests."""

    def __init__(self) -> None:
        super().__init__()
        self.register_called = False
        self.startup_called = False
        self.shutdown_called = False

    async def on_register(self, container):
        self.register_called = True
        container.set("sample.value", 1)

    async def on_startup(self, container):
        self.startup_called = container.get("sample.value") == 1

    async def on_shutdown(self, container):
        self.shutdown_called = True


@pytest.mark.asyncio
async def test_bento_module_lifecycle() -> None:
    container = BentoContainer()
    module = SampleModule()

    assert module.name == "sample"

    await module.on_register(container)
    await module.on_startup(container)
    await module.on_shutdown(container)

    assert module.register_called
    assert module.startup_called
    assert module.shutdown_called
    assert container.get("sample.value") == 1


class DummyEventBus:
    def __init__(self) -> None:
        self.closed = False

    async def close(self) -> None:  # pragma: no cover - exercised via MessagingManager cleanup
        self.closed = True


class DummyRuntime:
    """Minimal runtime stub exposing attributes referenced by managers."""

    def __init__(self) -> None:
        self._event_bus = None
        self.container = BentoContainer()


@pytest.mark.asyncio
async def test_messaging_manager_sets_event_bus(monkeypatch) -> None:
    runtime = cast("BentoRuntime", DummyRuntime())

    created = {"count": 0}

    class StubEventBus(DummyEventBus):
        def __init__(self) -> None:
            super().__init__()
            created["count"] += 1

    messaging_pkg = ModuleType("bento.messaging")
    messaging_pkg.__path__ = []  # type: ignore[attr-defined]
    event_bus_module = ModuleType("bento.messaging.event_bus")
    event_bus_module.InMemoryEventBus = StubEventBus  # type: ignore[attr-defined]
    messaging_pkg.event_bus = event_bus_module  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "bento.messaging", messaging_pkg)
    monkeypatch.setitem(sys.modules, "bento.messaging.event_bus", event_bus_module)

    manager = MessagingManager(runtime)
    manager.setup()
    assert created["count"] == 1
    assert runtime.container.get("event_bus") is runtime._event_bus

    # cleanup should close the event bus
    await manager.cleanup()
    assert runtime._event_bus is not None
    assert runtime._event_bus.closed
