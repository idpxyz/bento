"""Codec Package - Message serialization codecs.

This package provides codecs for serializing MessageEnvelopes to bytes
for transport over message brokers.

Available Codecs:
- JsonCodec: JSON serialization (simple, human-readable)
- AvroCodec: Avro serialization (schema evolution) - TODO
- ProtobufCodec: Protobuf serialization (efficient) - TODO
"""

import json

# Simple wrappers for quick JSON encode/decode usage
encode = json.dumps
decode = json.loads

# Re-export codecs and interfaces
from .base import MessageCodec  # noqa: E402,F401
from .json import JsonCodec  # noqa: E402,F401

__all__ = ["encode", "decode", "MessageCodec", "JsonCodec"]
