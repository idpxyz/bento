import json
from typing import Callable

import pulsar
from pydantic import ValidationError

from ..core.base_message import MessageEnvelope
from ..core.message_bus import AbstractMessageBus
from .config import get_pulsar_client


class PulsarMessageBus(AbstractMessageBus):
    def __init__(self):
        self.client = get_pulsar_client()
        self._producers = {}

    async def publish(self, topic: str, message: MessageEnvelope) -> None:
        if topic not in self._producers:
            self._producers[topic] = self.client.create_producer(topic)

        serialized = json.dumps(message.dict()).encode("utf-8")
        self._producers[topic].send(serialized)

    async def subscribe(self, topic: str, handler: Callable[[MessageEnvelope], None]) -> None:
        consumer = self.client.subscribe(topic, subscription_name="default-sub", consumer_type=pulsar.ConsumerType.Shared)

        while True:
            msg = consumer.receive()
            try:
                data = json.loads(msg.data())
                envelope = MessageEnvelope(**data)
                await handler(envelope)
                consumer.acknowledge(msg)
            except (json.JSONDecodeError, ValidationError) as e:
                consumer.negative_acknowledge(msg)
