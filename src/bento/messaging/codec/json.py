"""JSON Codec - JSON-based message serialization.

This module provides a JSON codec for MessageEnvelope serialization.
JSON is human-readable and widely supported, making it ideal for:
- Development and debugging
- Simple use cases
- Interoperability with external systems

For production systems requiring schema evolution or higher performance,
consider Avro or Protobuf codecs.
"""

import json
from typing import Any

from bento.messaging.envelope import MessageEnvelope


class JsonCodec:
    """JSON codec for MessageEnvelope serialization.

    Provides simple, human-readable JSON serialization for messages.

    Features:
    - Human-readable format
    - Easy debugging
    - Wide compatibility
    - No schema required

    Limitations:
    - Larger message size compared to binary formats
    - No schema evolution support
    - Less type safety

    Example:
        ```python
        from bento.messaging.codec.json import JsonCodec
        from bento.messaging.envelope import MessageEnvelope

        codec = JsonCodec()

        # Encoding
        envelope = MessageEnvelope(
            event_type="order.OrderCreated",
            payload={"order_id": "123"}
        )
        data = codec.encode(envelope)  # bytes

        # Decoding
        decoded = codec.decode(data)  # MessageEnvelope
        ```
    """

    def __init__(self, indent: int | None = None, ensure_ascii: bool = False) -> None:
        """Initialize JSON codec.

        Args:
            indent: JSON indentation (None for compact, 2/4 for pretty-print)
            ensure_ascii: If True, escape non-ASCII characters
        """
        self.indent = indent
        self.ensure_ascii = ensure_ascii

    def encode(self, envelope: MessageEnvelope) -> bytes:
        """Encode envelope to JSON bytes.

        Args:
            envelope: MessageEnvelope to encode

        Returns:
            JSON-encoded bytes (UTF-8)

        Raises:
            TypeError: If payload contains non-serializable objects
        """
        data = envelope.to_dict()
        json_str = json.dumps(
            data,
            indent=self.indent,
            ensure_ascii=self.ensure_ascii,
            default=self._json_serializer,
        )
        return json_str.encode("utf-8")

    def decode(self, data: bytes) -> MessageEnvelope:
        """Decode JSON bytes to envelope.

        Args:
            data: JSON-encoded bytes

        Returns:
            MessageEnvelope instance

        Raises:
            json.JSONDecodeError: If data is not valid JSON
            KeyError: If required fields are missing
        """
        json_str = data.decode("utf-8")
        envelope_dict = json.loads(json_str)
        return MessageEnvelope.from_dict(envelope_dict)

    @staticmethod
    def _json_serializer(obj: Any) -> Any:
        """Custom JSON serializer for non-standard types.

        Args:
            obj: Object to serialize

        Returns:
            JSON-serializable representation

        Raises:
            TypeError: If object is not serializable
        """
        # Handle datetime (already converted to ISO string in to_dict())
        # Handle other custom types if needed
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
