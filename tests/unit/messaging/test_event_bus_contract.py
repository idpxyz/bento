from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable

import pytest


class InMemoryEventBus:
    def __init__(self) -> None:
        self._subs: dict[str, list[Callable[[dict], Awaitable[None]]]] = defaultdict(list)

    def subscribe(self, topic: str, handler: Callable[[dict], Awaitable[None]]) -> None:
        self._subs[topic].append(handler)

    async def publish(self, topic: str, payload: dict) -> None:
        for h in self._subs.get(topic, []):
            await h(payload)


@pytest.mark.asyncio
async def test_publish_invokes_subscribers_in_order():
    bus = InMemoryEventBus()
    called: list[str] = []

    async def h1(p: dict) -> None:
        called.append("h1")

    async def h2(p: dict) -> None:
        await asyncio.sleep(0)
        called.append("h2")

    bus.subscribe("topic.a", h1)
    bus.subscribe("topic.a", h2)

    await bus.publish("topic.a", {"x": 1})

    assert called == ["h1", "h2"]


@pytest.mark.asyncio
async def test_topics_are_isolated():
    bus = InMemoryEventBus()
    called: list[str] = []

    async def h1(p: dict) -> None:
        called.append("a")

    async def h2(p: dict) -> None:
        called.append("b")

    bus.subscribe("topic.a", h1)
    bus.subscribe("topic.b", h2)

    await bus.publish("topic.a", {})
    assert called == ["a"]

    await bus.publish("topic.b", {})
    assert called == ["a", "b"]
