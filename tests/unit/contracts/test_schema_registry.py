from __future__ import annotations

from bento.contracts.schema_registry import EventSchemaRegistry


def test_schema_registry_loads_and_returns_schema(tmp_path):
    schema_dir = tmp_path / "contracts"
    schema_dir.mkdir()
    (schema_dir / "envelope.schema.json").write_text("{}", encoding="utf-8")
    schema_file = schema_dir / "user.schema.json"
    schema_file.write_text('{"title": "User"}', encoding="utf-8")

    registry = EventSchemaRegistry.from_dir(schema_dir)
    assert registry.has_schema("user")
    loaded = registry._event_schemas["user"]
    assert loaded["title"] == "User"


def test_schema_registry_returns_none_when_missing(tmp_path):
    # Create minimal envelope schema to allow initialization
    events_dir = tmp_path / "contracts"
    events_dir.mkdir()
    (events_dir / "envelope.schema.json").write_text("{}", encoding="utf-8")

    registry = EventSchemaRegistry.from_dir(events_dir)
    assert registry.has_schema("missing") is False
