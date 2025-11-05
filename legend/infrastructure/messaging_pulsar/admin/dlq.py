import json
from typing import List

import pulsar

from idp.framework.infrastructure.messaging.admin.client import PulsarAdminClient
from idp.framework.infrastructure.messaging.core.base_message import MessageEnvelope
from idp.framework.infrastructure.messaging.core.codec import (
    _codec_registry,
    get_codec,
    register_codec,
)
from idp.framework.infrastructure.messaging.pulsar.config import get_pulsar_client


class DLQAdmin:
    def __init__(self, admin_client: PulsarAdminClient):
        self.admin_client = admin_client
        self.client = get_pulsar_client()
        
        # Ensure JSON codec is registered
        if "json" not in _codec_registry:
            # Import the codec directly if not already registered
            from idp.framework.infrastructure.messaging.codec.json import (
                JsonMessageCodec,
            )
            register_codec("json", JsonMessageCodec())
            
        self.codec = get_codec("json")

    async def list_dlq_topics(self, tenant: str, namespace: str) -> List[str]:
        """
        列出某命名空间下的所有 .dlq Topic
        """
        path = f'/admin/v2/persistent/{tenant}/{namespace}'
        topics = await self.admin_client.get(path)
        return [t for t in topics if t.endswith(".dlq")]

    async def get_dlq_stats(self, tenant: str, namespace: str, topic: str) -> dict:
        """
        获取 DLQ Topic 的 backlog 等状态
        """
        topic_path = f'/admin/v2/persistent/{tenant}/{namespace}/{topic}/stats'
        return await self.admin_client.get(topic_path)

    async def clear_dlq(self, tenant: str, namespace: str, topic: str):
        """
        删除 DLQ Topic（等同于清空消息）
        """
        path = f'/admin/v2/persistent/{tenant}/{namespace}/{topic}?force=true'
        await self.admin_client.delete(path)

    async def replay_dlq(self, tenant: str, namespace: str, topic: str, max_messages: int = 10):
        """
        从 DLQ 中读取消息，并重新发布到原始 Topic
        """
        full_topic = f'persistent://{tenant}/{namespace}/{topic}'
        consumer = self.client.subscribe(
            full_topic,
            subscription_name="dlq-replay",
            consumer_type=pulsar.ConsumerType.Exclusive
        )

        count = 0
        while count < max_messages:
            try:
                msg = consumer.receive(timeout_millis=3000)
                data = json.loads(msg.data())
                event_type = data["event_type"]
                original_topic = f'persistent://{tenant}/{namespace}/{event_type}'

                envelope = MessageEnvelope(
                    event_type=event_type,
                    payload=data["payload"],
                    source=data["source"],
                    correlation_id=data["correlation_id"],
                    occurred_at=data["occurred_at"],
                )

                producer = self.client.create_producer(original_topic)
                producer.send(self.codec.encode(envelope))

                consumer.acknowledge(msg)
                print(f"[DLQ Replay] 已重发事件 {event_type} trace={envelope.correlation_id}")
                count += 1

            except Exception as e:
                print(f"[DLQ Error] 消息重发失败: {e}")
                consumer.negative_acknowledge(msg)


# 实用方式示例
# admin = DLQAdmin(PulsarAdminClient("http://localhost:8080"))

# # 列出所有 DLQ Topic
# await admin.list_dlq_topics("public", "default")

# # 查看 backlog 状态
# await admin.get_dlq_stats("public", "default", "user.registered.dlq")

# # 清空某个 DLQ
# await admin.clear_dlq("public", "default", "user.registered.dlq")

# # 手动补偿
# await admin.replay_dlq("public", "default", "user.registered.dlq", max_messages=5)
