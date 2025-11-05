from idp.framework.infrastructure.messaging.core.subscriber import AbstractEventSubscriber
import pulsar
import asyncio
from idp.framework.domain.base.event import DomainEvent

class PulsarEventSubscriber(AbstractEventSubscriber):
    def __init__(self, client: pulsar.Client):
        self._client = client

    async def subscribe(self, topic, handler, *, tenant_id=None):
        sub_name = f"{tenant_id or 'app'}-sub"
        consumer = self._client.subscribe(topic, sub_name,
                                          schema=pulsar.schema.BytesSchema())
        loop = asyncio.get_running_loop()
        while True:
            msg = await loop.run_in_executor(None, consumer.receive)
            try:
                evt = DomainEvent.model_validate_json(msg.data())
                await handler(evt)          # app-level handler
                consumer.acknowledge(msg)
            except Exception:
                consumer.negative_acknowledge(msg)
