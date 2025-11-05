"""Codec Package - Message serialization codecs.

This package provides codecs for serializing MessageEnvelopes to bytes
for transport over message brokers.

Available Codecs:
- JsonCodec: JSON serialization (simple, human-readable)
- AvroCodec: Avro serialization (schema evolution) - TODO
- ProtobufCodec: Protobuf serialization (efficient) - TODO
"""

from bento.messaging.codec.base import MessageCodec
from bento.messaging.codec.json import JsonCodec

__all__ = [
    "MessageCodec",
    "JsonCodec",
]

