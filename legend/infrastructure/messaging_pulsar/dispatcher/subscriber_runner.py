import asyncio
from typing import List

from ..pulsar.event_bus import PulsarEventBus


async def run_event_subscribers(topics: List[str]):
    event_bus = PulsarEventBus()
    tasks = [event_bus.run_subscription(topic) for topic in topics]
    await asyncio.gather(*tasks)
