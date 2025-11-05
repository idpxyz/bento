import json
from typing import List

import pulsar

from ..core.base_message import MessageEnvelope
from ..core.codec import get_codec
from ..pulsar.config import get_pulsar_client


class DLQConsumer:
    def __init__(self):
        self.client = get_pulsar_client()
        self.codec = get_codec("json")  # 和主消息系统保持一致

    def get_dlq_topic(self, event_type: str) -> str:
        return f"persistent://public/default/{event_type}.dlq"

    def replay(self, dlq_topic: str, max_messages: int = 10):
        """
        从 DLQ topic 中读取失败消息，并重发到原始 topic
        """
        consumer = self.client.subscribe(
            dlq_topic,
            subscription_name="dlq-inspector",
            consumer_type=pulsar.ConsumerType.Exclusive
        )

        count = 0
        while count < max_messages:
            msg = consumer.receive(timeout_millis=3000)
            if not msg:
                break

            try:
                data = json.loads(msg.data())
                event_type = data["event_type"]
                original_topic = f"persistent://public/default/{event_type}"
                envelope = MessageEnvelope(
                    event_type=event_type,
                    payload=data["payload"],
                    source=data["source"],
                    correlation_id=data["correlation_id"],
                    occurred_at=data["occurred_at"],
                )

                # 重发
                producer = self.client.create_producer(original_topic)
                producer.send(self.codec.encode(envelope))

                consumer.acknowledge(msg)
                print(f"[DLQ Replay] {event_type} 已重发，trace_id={envelope.correlation_id}")
                count += 1
            except Exception as e:
                print(f"[DLQ ERROR] 重发失败: {e}")
                consumer.negative_acknowledge(msg)


# 实用方式示例
# from infrastructure.messaging.dlq.dlq_consumer import DLQConsumer

# dlq = DLQConsumer()
# dlq.replay("persistent://public/default/user.registered.dlq", max_messages=5)
