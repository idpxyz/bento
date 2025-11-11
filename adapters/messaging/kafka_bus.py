from __future__ import annotations

from collections.abc import Awaitable, Callable

try:
    from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
except Exception:  # pragma: no cover
    AIOKafkaProducer = AIOKafkaConsumer = None  # type: ignore


class KafkaEventBus:
    def __init__(self, brokers: str = "localhost:9092", group_id: str = "omnia-ddd"):
        assert AIOKafkaProducer is not None, "aiokafka not installed"
        self.producer = AIOKafkaProducer(bootstrap_servers=brokers)
        self.brokers = brokers
        self.group_id = group_id
        self._handlers: dict[str, list[Callable[[dict], Awaitable[None]]]] = {}

    async def start(self):
        await self.producer.start()

    async def stop(self):
        await self.producer.stop()

    async def publish(self, topic: str, payload: dict) -> None:
        import json

        await self.producer.send_and_wait(topic, json.dumps(payload).encode("utf-8"))

    def subscribe(self, topic: str, handler: Callable[[dict], Awaitable[None]]) -> None:
        self._handlers.setdefault(topic, []).append(handler)
        # Note: minimal skeleton; a real consumer loop should be spawned to poll and dispatch.
