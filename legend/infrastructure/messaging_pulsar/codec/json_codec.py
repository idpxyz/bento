import json
from datetime import datetime

from idp.framework.infrastructure.messaging.core.base_message import MessageEnvelope
from idp.framework.infrastructure.messaging.core.codec import (
    MessageCodec,
    register_codec,
)


class DateTimeEncoder(json.JSONEncoder):
    """自定义 JSON 编码器，支持 datetime 类型序列化"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class JsonMessageCodec(MessageCodec):
    def encode(self, envelope: MessageEnvelope) -> bytes:
        return json.dumps(envelope.model_dump(), cls=DateTimeEncoder).encode("utf-8")

    def decode(self, raw: bytes) -> MessageEnvelope:
        data = json.loads(raw)
        return MessageEnvelope(**data)

# 注册 Codec（必须执行）
register_codec("json", JsonMessageCodec()) 