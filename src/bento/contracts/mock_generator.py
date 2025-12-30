"""Mock Data Generator - Contracts-as-Code.

Generates mock/test data from JSON schemas for testing and development.
Supports all JSON Schema types and provides realistic data generation.

Example:
    ```python
    from bento.contracts import MockGenerator

    schema = {
        "type": "object",
        "properties": {
            "id": {"type": "string", "pattern": "^[0-9]+$"},
            "name": {"type": "string", "minLength": 1},
            "email": {"type": "string", "format": "email"},
            "age": {"type": "integer", "minimum": 0, "maximum": 150},
            "tags": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["id", "name"],
    }

    generator = MockGenerator()
    mock_data = generator.generate(schema)
    # → {"id": "12345", "name": "John Doe", "email": "john@example.com", ...}
    ```
"""

from __future__ import annotations

import random
import string
import uuid
from typing import Any


class MockGenerator:
    """Generates mock data from JSON schemas.

    Supports all JSON Schema types and provides realistic data generation
    for testing and development purposes.

    Example:
        ```python
        generator = MockGenerator()

        # Generate single mock object
        mock = generator.generate(schema)

        # Generate multiple mock objects
        mocks = generator.generate_batch(schema, count=10)

        # Generate with custom seed for reproducibility
        generator = MockGenerator(seed=42)
        mock = generator.generate(schema)
        ```
    """

    def __init__(self, seed: int | None = None):
        """Initialize generator with optional seed.

        Args:
            seed: Random seed for reproducibility
        """
        if seed is not None:
            random.seed(seed)
        self.seed = seed

    def generate(self, schema: dict[str, Any]) -> Any:
        """Generate mock data from schema.

        Args:
            schema: JSON schema definition

        Returns:
            Generated mock data matching the schema
        """
        return self._generate_value(schema)

    def generate_batch(
        self,
        schema: dict[str, Any],
        count: int = 10,
    ) -> list[Any]:
        """Generate multiple mock objects.

        Args:
            schema: JSON schema definition
            count: Number of mock objects to generate

        Returns:
            List of generated mock data
        """
        return [self.generate(schema) for _ in range(count)]

    def _generate_value(self, schema: dict[str, Any]) -> Any:
        """Generate value based on schema type."""
        schema_type = schema.get("type")

        # Handle enum
        if "enum" in schema:
            return random.choice(schema["enum"])

        # Handle const
        if "const" in schema:
            return schema["const"]

        # Handle by type
        if schema_type == "object":
            return self._generate_object(schema)
        elif schema_type == "array":
            return self._generate_array(schema)
        elif schema_type == "string":
            return self._generate_string(schema)
        elif schema_type == "number":
            return self._generate_number(schema)
        elif schema_type == "integer":
            return self._generate_integer(schema)
        elif schema_type == "boolean":
            return random.choice([True, False])
        elif schema_type == "null":
            return None
        else:
            # Default to string
            return self._generate_string(schema)

    def _generate_object(self, schema: dict[str, Any]) -> dict[str, Any]:
        """Generate object/dict."""
        properties = schema.get("properties", {})
        required = set(schema.get("required", []))

        result = {}

        # Generate required properties
        for prop_name in required:
            if prop_name in properties:
                result[prop_name] = self._generate_value(properties[prop_name])

        # Optionally generate optional properties (50% chance)
        for prop_name, prop_schema in properties.items():
            if prop_name not in result and random.random() < 0.5:
                result[prop_name] = self._generate_value(prop_schema)

        return result

    def _generate_array(self, schema: dict[str, Any]) -> list[Any]:
        """Generate array."""
        items_schema = schema.get("items", {})
        min_items = schema.get("minItems", 0)
        max_items = schema.get("maxItems", 5)

        # Generate random length between min and max
        length = random.randint(min_items, max_items)

        return [self._generate_value(items_schema) for _ in range(length)]

    def _generate_string(self, schema: dict[str, Any]) -> str:
        """Generate string."""
        string_format = schema.get("format")
        pattern = schema.get("pattern")
        min_length = schema.get("minLength", 1)
        max_length = schema.get("maxLength", 20)

        # Handle specific formats
        if string_format == "email":
            return f"{self._random_string(8)}@example.com"
        elif string_format == "uuid":
            return str(uuid.uuid4())
        elif string_format == "date":
            return "2024-01-15"
        elif string_format == "date-time":
            return "2024-01-15T10:30:00Z"
        elif string_format == "time":
            return "10:30:00"
        elif string_format == "uri":
            return f"https://example.com/{self._random_string(8)}"
        elif string_format == "ipv4":
            return f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}"
        elif string_format == "ipv6":
            return ":".join(f"{random.randint(0, 0xFFFF):x}" for _ in range(8))
        elif pattern:
            # For patterns, just generate a string that might match
            # (full regex matching is complex, so we do simple approach)
            return self._generate_from_pattern(pattern, min_length, max_length)
        else:
            # Generate random string
            length = random.randint(min_length, max_length)
            return self._random_string(length)

    def _generate_number(self, schema: dict[str, Any]) -> float:
        """Generate number."""
        minimum = schema.get("minimum", 0.0)
        maximum = schema.get("maximum", 100.0)
        exclusive_minimum = schema.get("exclusiveMinimum")
        exclusive_maximum = schema.get("exclusiveMaximum")

        if exclusive_minimum is not None:
            minimum = exclusive_minimum + 0.01
        if exclusive_maximum is not None:
            maximum = exclusive_maximum - 0.01

        return random.uniform(minimum, maximum)

    def _generate_integer(self, schema: dict[str, Any]) -> int:
        """Generate integer."""
        minimum = schema.get("minimum", 0)
        maximum = schema.get("maximum", 100)
        exclusive_minimum = schema.get("exclusiveMinimum")
        exclusive_maximum = schema.get("exclusiveMaximum")

        if exclusive_minimum is not None:
            minimum = exclusive_minimum + 1
        if exclusive_maximum is not None:
            maximum = exclusive_maximum - 1

        return random.randint(minimum, maximum)

    def _random_string(self, length: int) -> str:
        """Generate random alphanumeric string."""
        return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))

    def _generate_from_pattern(
        self,
        pattern: str,
        min_length: int,
        max_length: int,
    ) -> str:
        """Generate string from regex pattern (simplified).

        Args:
            pattern: Regex pattern
            min_length: Minimum length
            max_length: Maximum length

        Returns:
            Generated string
        """
        # Simple pattern handling for common cases
        if pattern == "^[0-9]+$":
            length = random.randint(min_length, max_length)
            return "".join(random.choices(string.digits, k=length))
        elif pattern == "^[a-z]+$":
            length = random.randint(min_length, max_length)
            return "".join(random.choices(string.ascii_lowercase, k=length))
        elif pattern == "^[A-Z]+$":
            length = random.randint(min_length, max_length)
            return "".join(random.choices(string.ascii_uppercase, k=length))
        elif pattern == "^[a-zA-Z0-9]+$":
            length = random.randint(min_length, max_length)
            return "".join(random.choices(string.ascii_letters + string.digits, k=length))
        else:
            # Fallback: generate random string
            length = random.randint(min_length, max_length)
            return self._random_string(length)
