from abc import ABC, abstractmethod
from typing import Dict, Type

from ..core.base_message import MessageEnvelope


class MessageCodec(ABC):
    """
    抽象编码器：支持将消息在二进制 ↔ MessageEnvelope 间转换
    """

    @abstractmethod
    def encode(self, envelope: MessageEnvelope) -> bytes:
        ...

    @abstractmethod
    def decode(self, raw: bytes) -> MessageEnvelope:
        ...


# 默认全局注册表（可支持不同 event_type 使用不同 codec）
_codec_registry: Dict[str, MessageCodec] = {}

def register_codec(name: str, codec: MessageCodec):
    _codec_registry[name] = codec

def get_codec(name: str = "json") -> MessageCodec:
    return _codec_registry[name]
