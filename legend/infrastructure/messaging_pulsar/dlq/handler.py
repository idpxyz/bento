import json

from ..core.base_message import MessageEnvelope
from ..pulsar.config import get_pulsar_client


def get_dlq_topic(event_type: str) -> str:
    return f"persistent://public/default/{event_type}.dlq"


def write_to_dlq(event: MessageEnvelope, reason: str):
    """
    将失败消息写入 DLQ topic（格式：event_type + `.dlq` 后缀）
    """
    client = get_pulsar_client()
    topic = get_dlq_topic(event.event_type)
    producer = client.create_producer(topic)

    message = {
        "event_type": event.event_type,
        "payload": event.payload,
        "source": event.source,
        "correlation_id": event.correlation_id,
        "occurred_at": str(event.occurred_at),
        "dlq_reason": reason,
    }

    producer.send(json.dumps(message).encode("utf-8"))
