import json
from typing import Callable, Optional

import pulsar

from idp.framework.domain.messaging.event import DomainEvent
from idp.framework.infrastructure.messaging.serialization.json.codec import (
    JsonMessageCodec,
)


class PulsarMessageBus:
    """Pulsar消息总线实现"""
    
    def __init__(
        self,
        client: pulsar.Client,
        codec: Optional[JsonMessageCodec] = None
    ):
        self.client = client
        self.codec = codec or JsonMessageCodec()
        self._producers = {}
        self._consumers = {}
    
    async def publish(self, topic: str, event: DomainEvent) -> None:
        """发布事件到指定主题"""
        if topic not in self._producers:
            self._producers[topic] = self.client.create_producer(topic)
        
        producer = self._producers[topic]
        message = self.codec.encode(event)
        await producer.send(message)
    
    async def subscribe(
        self,
        topic: str,
        handler: Callable[[DomainEvent], None],
        subscription_name: str
    ) -> None:
        """订阅主题"""
        if topic not in self._consumers:
            self._consumers[topic] = self.client.subscribe(
                topic,
                subscription_name=subscription_name,
                consumer_type=pulsar.ConsumerType.Failover
            )
        
        consumer = self._consumers[topic]
        
        while True:
            msg = await consumer.receive()
            try:
                event = self.codec.decode(msg.data())
                await handler(event)
                await consumer.acknowledge(msg)
            except Exception as e:
                await consumer.negative_acknowledge(msg)
                raise e
    
    async def close(self) -> None:
        """关闭连接"""
        for producer in self._producers.values():
            await producer.close()
        
        for consumer in self._consumers.values():
            await consumer.close()
        
        await self.client.close() 