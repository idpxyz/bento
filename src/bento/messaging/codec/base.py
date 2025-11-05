"""Codec Base - Protocol and base classes for message serialization.

This module defines the codec interface for serializing and deserializing
MessageEnvelopes to/from bytes for transport over message brokers.
"""

from typing import Protocol

from bento.messaging.envelope import MessageEnvelope


class MessageCodec(Protocol):
    """Protocol for message serialization and deserialization.

    Defines the interface for encoding MessageEnvelopes to bytes and
    decoding bytes back to MessageEnvelopes.

    Implementations can use different serialization formats:
    - JSON (simple, human-readable)
    - Avro (schema evolution support)
    - Protobuf (efficient, type-safe)

    Example:
        ```python
        class MyCodec:
            def encode(self, envelope: MessageEnvelope) -> bytes:
                return serialize(envelope)

            def decode(self, data: bytes) -> MessageEnvelope:
                return deserialize(data)
        ```
    """

    def encode(self, envelope: MessageEnvelope) -> bytes:
        """Encode envelope to bytes.

        Args:
            envelope: MessageEnvelope to encode

        Returns:
            Serialized bytes

        Raises:
            EncodingError: If encoding fails
        """
        ...

    def decode(self, data: bytes) -> MessageEnvelope:
        """Decode bytes to envelope.

        Args:
            data: Serialized bytes

        Returns:
            MessageEnvelope instance

        Raises:
            DecodingError: If decoding fails
        """
        ...
