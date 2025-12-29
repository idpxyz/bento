"""Tests for CompatibilityValidator."""

from bento.contracts.compatibility_validator import (
    CompatibilityMode,
    CompatibilityValidator,
)


class TestCompatibilityValidator:
    """Test compatibility validation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = CompatibilityValidator()

    def test_backward_compatible_added_optional_property(self):
        """Test backward compatibility with added optional property."""
        old_schema = {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
            },
            "required": ["id"],
        }
        new_schema = {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
            },
            "required": ["id"],
        }

        result = self.validator.validate_backward_compatible(old_schema, new_schema)

        assert result.is_compatible
        assert result.mode == CompatibilityMode.BACKWARD

    def test_backward_incompatible_removed_property(self):
        """Test backward incompatibility with removed property."""
        old_schema = {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
            },
            "required": ["id"],
        }
        new_schema = {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
            },
            "required": ["id"],
        }

        result = self.validator.validate_backward_compatible(old_schema, new_schema)

        assert not result.is_compatible
        assert len(result.breaking_changes) > 0

    def test_backward_incompatible_required_field_added(self):
        """Test backward incompatibility with newly required field."""
        old_schema = {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
            },
            "required": ["id"],
        }
        new_schema = {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
            },
            "required": ["id", "name"],
        }

        result = self.validator.validate_backward_compatible(old_schema, new_schema)

        assert not result.is_compatible
        assert len(result.breaking_changes) > 0

    def test_forward_compatible_removed_required_field(self):
        """Test forward compatibility with removed required field.

        Forward compatibility: old schema must accept new data.
        If old schema requires 'name' but new schema doesn't have it,
        old schema cannot accept new data -> NOT compatible.
        """
        old_schema = {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
            },
            "required": ["id", "name"],
        }
        new_schema = {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
            },
            "required": ["id"],
        }

        result = self.validator.validate_forward_compatible(old_schema, new_schema)

        # Old schema requires 'name', but new schema doesn't provide it
        # So old schema cannot accept new data -> NOT compatible
        assert not result.is_compatible
        assert result.mode == CompatibilityMode.FORWARD

    def test_full_compatibility_no_changes(self):
        """Test full compatibility with no changes."""
        schema = {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
            },
            "required": ["id"],
        }

        result = self.validator.validate_full_compatible(schema, schema)

        assert result.is_compatible
        assert result.mode == CompatibilityMode.FULL

    def test_full_incompatibility_breaking_change(self):
        """Test full incompatibility with breaking change."""
        old_schema = {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
            },
            "required": ["id"],
        }
        new_schema = {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
            },
            "required": ["id"],
        }

        result = self.validator.validate_full_compatible(old_schema, new_schema)

        assert not result.is_compatible
        assert result.mode == CompatibilityMode.FULL

    def test_compatibility_result_string_representation(self):
        """Test compatibility result string representation."""
        old_schema = {
            "type": "object",
            "properties": {"id": {"type": "string"}},
        }
        new_schema = {
            "type": "object",
            "properties": {},
        }

        result = self.validator.validate_backward_compatible(old_schema, new_schema)

        result_str = str(result)
        assert "Compatibility Result" in result_str
        assert "backward" in result_str

    def test_migration_guide_provided(self):
        """Test that migration guide is provided."""
        old_schema = {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
            },
            "required": ["id"],
        }
        new_schema = {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
            },
            "required": ["id", "name"],
        }

        result = self.validator.validate_backward_compatible(old_schema, new_schema)

        assert len(result.migration_guide) > 0

    def test_compatibility_matrix(self):
        """Test compatibility matrix generation."""
        schemas = {
            "v1": {
                "type": "object",
                "properties": {"id": {"type": "string"}},
            },
            "v2": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                },
            },
        }

        matrix = self.validator.get_compatibility_matrix(schemas)

        assert "v1" in matrix
        assert "v2" in matrix
        assert matrix["v1"]["v1"] is True
        assert matrix["v2"]["v2"] is True

    def test_migration_path(self):
        """Test migration path generation."""
        old_schema = {
            "type": "object",
            "properties": {"id": {"type": "string"}},
        }
        new_schema = {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
            },
        }

        path = self.validator.get_migration_path(old_schema, new_schema)

        assert isinstance(path, list)
        assert len(path) > 0
        assert any("Migration" in step for step in path)

    def test_additional_properties_restriction_backward_incompatible(self):
        """Test backward incompatibility with additionalProperties restriction."""
        old_schema = {
            "type": "object",
            "properties": {"id": {"type": "string"}},
            "additionalProperties": True,
        }
        new_schema = {
            "type": "object",
            "properties": {"id": {"type": "string"}},
            "additionalProperties": False,
        }

        result = self.validator.validate_backward_compatible(old_schema, new_schema)

        assert not result.is_compatible
        assert len(result.breaking_changes) > 0

    def test_multiple_incompatibilities(self):
        """Test detection of multiple incompatibilities."""
        old_schema = {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "email": {"type": "string"},
                "status": {"type": "string", "enum": ["ACTIVE", "INACTIVE"]},
            },
            "required": ["id"],
        }
        new_schema = {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "status": {"type": "string", "enum": ["ACTIVE"]},
            },
            "required": ["id", "status"],
        }

        result = self.validator.validate_backward_compatible(old_schema, new_schema)

        assert not result.is_compatible
        assert len(result.breaking_changes) >= 2
        assert len(result.issues) >= 2
