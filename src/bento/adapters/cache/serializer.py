"""Cache Serializer - Handles serialization of domain objects for caching.

This module provides a unified serialization mechanism for cache backends.
It automatically detects and serializes aggregate roots and other domain objects.
"""

import json
import pickle
from typing import Any

from bento.adapters.cache.config import SerializerType


class CacheSerializer:
    """Cache serializer for domain objects.

    Provides automatic serialization of:
    - Aggregate roots (via to_cache_dict())
    - Lists of domain objects
    - Nested structures
    - Primitive types

    This is a stateless utility class that can be shared across cache implementations.
    """

    @staticmethod
    def make_serializable(value: Any) -> Any:
        """Convert value to JSON-serializable format.

        Automatically handles:
        - Aggregate roots with to_cache_dict() method
        - Lists of aggregate roots
        - Nested structures (dicts, lists)
        - Primitive types (str, int, float, bool, None)

        Args:
            value: Value to make serializable

        Returns:
            JSON-serializable value (dict, list, or primitive)

        Example:
            ```python
            # Serialize aggregate root
            product = Product(id=ID("123"), name="iPhone")
            serializable = CacheSerializer.make_serializable(product)
            # Returns: {"id": "123", "name": "iPhone", ...}

            # Serialize list of aggregate roots
            products = [product1, product2]
            serializable = CacheSerializer.make_serializable(products)
            # Returns: [{"id": "1", ...}, {"id": "2", ...}]
            ```
        """
        # Check if object has to_cache_dict method (AggregateRoot, Entity, etc.)
        if hasattr(value, "to_cache_dict") and callable(value.to_cache_dict):
            return value.to_cache_dict()

        # Handle lists - recursively serialize each item
        if isinstance(value, list):
            return [CacheSerializer.make_serializable(item) for item in value]

        # Handle dicts - recursively serialize each value
        if isinstance(value, dict):
            return {k: CacheSerializer.make_serializable(v) for k, v in value.items()}

        # Primitive types and already serializable (str, int, float, bool, None)
        return value

    @staticmethod
    def serialize(value: Any, serializer_type: SerializerType = SerializerType.JSON) -> bytes:
        """Serialize value to bytes.

        Args:
            value: Value to serialize
            serializer_type: Serialization format (JSON or PICKLE)

        Returns:
            Serialized bytes

        Raises:
            ValueError: If serialization fails
        """
        try:
            if serializer_type == SerializerType.JSON:
                # Auto-convert to serializable format first
                serializable_value = CacheSerializer.make_serializable(value)
                return json.dumps(serializable_value).encode("utf-8")
            else:  # PICKLE
                return pickle.dumps(value)
        except Exception as e:
            raise ValueError(f"Failed to serialize value: {e}") from e

    @staticmethod
    def deserialize(data: bytes, serializer_type: SerializerType = SerializerType.JSON) -> Any:
        """Deserialize bytes to value.

        Args:
            data: Serialized bytes
            serializer_type: Serialization format (JSON or PICKLE)

        Returns:
            Deserialized value

        Raises:
            ValueError: If deserialization fails
        """
        try:
            if serializer_type == SerializerType.JSON:
                return json.loads(data.decode("utf-8"))
            else:  # PICKLE
                return pickle.loads(data)
        except Exception as e:
            raise ValueError(f"Failed to deserialize value: {e}") from e
