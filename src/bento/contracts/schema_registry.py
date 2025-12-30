"""Event Schema Registry - Contracts-as-Code.

Validates event envelopes and payloads against JSON schemas.
Uses JSON Schema Draft 2020-12 for validation.

Schema Directory Structure:
    ```
    contracts/events/
    ├── envelope.schema.json      # CloudEvents envelope schema
    ├── OrderCreated.v1.schema.json
    ├── OrderUpdated.v1.schema.json
    └── ...
    ```
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

try:
    from jsonschema import Draft202012Validator

    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False
    Draft202012Validator = None



class EventSchemaRegistry:
    """Registry of event schemas for validation.

    Loads envelope and event schemas from the contracts directory
    and provides validation methods.

    Example:
        ```python
        registry = EventSchemaRegistry.from_dir(Path("contracts/events"))

        # Validate envelope structure
        registry.validate_envelope(event)

        # Validate specific event payload
        registry.validate_event("OrderCreated", event)
        ```
    """

    def __init__(
        self,
        envelope_schema: dict[str, Any],
        event_schemas: dict[str, dict[str, Any]],
    ):
        """Initialize registry with schemas.

        Args:
            envelope_schema: JSON schema for event envelope
            event_schemas: Dict mapping event type to its JSON schema
        """
        if not HAS_JSONSCHEMA:
            raise ImportError(
                "jsonschema is required for EventSchemaRegistry. "
                "Install with: pip install jsonschema"
            )

        assert Draft202012Validator is not None
        self._envelope = Draft202012Validator(envelope_schema)
        self._events = {k: Draft202012Validator(v) for k, v in event_schemas.items()}
        self._envelope_schema = envelope_schema
        self._event_schemas = event_schemas

    @classmethod
    def from_dir(cls, events_dir: pathlib.Path) -> EventSchemaRegistry:
        """Load schemas from a directory containing JSON schema files.

        Expected structure:
        - envelope.schema.json (required)
        - *.schema.json for each event type

        Args:
            events_dir: Path to events schema directory

        Returns:
            Configured EventSchemaRegistry

        Raises:
            FileNotFoundError: If envelope schema is missing
        """
        envelope_path = events_dir / "envelope.schema.json"
        if not envelope_path.exists():
            raise FileNotFoundError(f"Envelope schema not found: {envelope_path}")

        envelope = json.loads(envelope_path.read_text(encoding="utf-8"))

        event_schemas: dict[str, dict[str, Any]] = {}
        for p in events_dir.rglob("*.schema.json"):
            if p.name == "envelope.schema.json":
                continue
            doc = json.loads(p.read_text(encoding="utf-8"))
            # Extract event type from filename: OrderCreated.v1.schema.json -> OrderCreated
            event_type = p.stem.replace(".schema", "").replace(".v1", "")
            event_schemas[event_type] = doc

        return cls(envelope, event_schemas)

    def validate_envelope(self, envelope: dict[str, Any]) -> None:
        """Validate an event envelope against the envelope schema.

        Args:
            envelope: Event envelope to validate

        Raises:
            SchemaValidationError: If validation fails
        """
        errors = sorted(self._envelope.iter_errors(envelope), key=lambda e: e.path)
        if errors:
            raise SchemaValidationError(
                f"Envelope schema invalid: {errors[0].message}",
                errors=errors,
            )

    def validate_event(self, event_type: str, payload: dict[str, Any]) -> None:
        """Validate an event payload against its schema.

        Args:
            event_type: Type of event
            payload: Event payload to validate

        Raises:
            KeyError: If event type has no schema
            SchemaValidationError: If validation fails
        """
        validator = self._events.get(event_type)
        if not validator:
            raise KeyError(f"Unknown event schema: {event_type}")

        errors = sorted(validator.iter_errors(payload), key=lambda e: e.path)
        if errors:
            raise SchemaValidationError(
                f"Event schema invalid ({event_type}): {errors[0].message}",
                errors=errors,
            )

    def has_schema(self, event_type: str) -> bool:
        """Check if a schema exists for an event type.

        Args:
            event_type: Type of event

        Returns:
            True if schema exists
        """
        return event_type in self._events

    @property
    def event_types(self) -> list[str]:
        """Get list of all registered event types."""
        return list(self._events.keys())


class SchemaValidationError(Exception):
    """Raised when schema validation fails.

    Attributes:
        message: Error message
        errors: List of validation errors from jsonschema
    """

    def __init__(self, message: str, errors: list | None = None):
        super().__init__(message)
        self.message = message
        self.errors = errors or []
