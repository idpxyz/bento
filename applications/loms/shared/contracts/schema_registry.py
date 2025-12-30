"""
Event Schema Registry - Contracts-as-Code.

Validates event envelopes and payloads against JSON schemas.
"""
import json
import pathlib

from jsonschema import Draft202012Validator


class EventSchemaRegistry:
    """
    Registry of event schemas for validation.

    Loads envelope and event schemas from the contracts directory.
    """

    def __init__(self, envelope_schema: dict, event_schemas: dict[str, dict]):
        self._envelope = Draft202012Validator(envelope_schema)
        self._events = {k: Draft202012Validator(v) for k, v in event_schemas.items()}

    @staticmethod
    def from_dir(events_dir: pathlib.Path) -> "EventSchemaRegistry":
        """Load schemas from a directory containing JSON schema files."""
        envelope = json.loads((events_dir / "envelope.schema.json").read_text(encoding="utf-8"))
        event_schemas: dict[str, dict] = {}
        for p in events_dir.rglob("*.schema.json"):
            if p.name == "envelope.schema.json":
                continue
            doc = json.loads(p.read_text(encoding="utf-8"))
            event_type = p.stem.replace(".v1", "")
            event_schemas[event_type] = doc
        return EventSchemaRegistry(envelope, event_schemas)

    def validate_envelope(self, envelope: dict) -> None:
        """Validate an event envelope against the envelope schema."""
        errors = sorted(self._envelope.iter_errors(envelope), key=lambda e: e.path)
        if errors:
            raise ValueError(f"Envelope schema invalid: {errors[0].message}")

    def validate_event(self, event_type: str, envelope: dict) -> None:
        """Validate an event payload against its schema."""
        v = self._events.get(event_type)
        if not v:
            raise KeyError(f"Unknown event schema: {event_type}")
        errors = sorted(v.iter_errors(envelope), key=lambda e: e.path)
        if errors:
            raise ValueError(f"Event schema invalid ({event_type}): {errors[0].message}")
