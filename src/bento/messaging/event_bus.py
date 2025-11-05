from collections.abc import Awaitable, Callable
from typing import Protocol


class EventBus(Protocol):
    async def publish(self, topic: str, payload: dict) -> None: ...
    def subscribe(self, topic: str, handler: Callable[[dict], Awaitable[None]]) -> None: ...
