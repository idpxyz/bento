"""Tests for SchemaComparator."""

from bento.contracts.schema_comparator import SchemaComparator


class TestSchemaComparator:
    """Test schema comparison."""

    def setup_method(self):
        """Set up test fixtures."""
        self.comparator = SchemaComparator()

    def test_compare_identical_schemas(self):
        """Test comparison of identical schemas."""
        schema = {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
            },
        }

        diff = self.comparator.compare(schema, schema)

        assert not diff.has_changes
        assert len(diff.added_keys) == 0
        assert len(diff.removed_keys) == 0
        assert len(diff.modified_keys) == 0

    def test_compare_added_keys(self):
        """Test comparison with added keys."""
        old_schema = {
            "type": "object",
            "properties": {"id": {"type": "string"}},
        }
        new_schema = {
            "type": "object",
            "properties": {"id": {"type": "string"}},
            "required": ["id"],
        }

        diff = self.comparator.compare(old_schema, new_schema)

        assert diff.has_changes
        assert "required" in diff.added_keys

    def test_compare_removed_keys(self):
        """Test comparison with removed keys."""
        old_schema = {
            "type": "object",
            "properties": {"id": {"type": "string"}},
            "required": ["id"],
        }
        new_schema = {
            "type": "object",
            "properties": {"id": {"type": "string"}},
        }

        diff = self.comparator.compare(old_schema, new_schema)

        assert diff.has_changes
        assert "required" in diff.removed_keys

    def test_compare_modified_keys(self):
        """Test comparison with modified keys."""
        old_schema = {
            "type": "object",
            "minProperties": 1,
        }
        new_schema = {
            "type": "object",
            "minProperties": 2,
        }

        diff = self.comparator.compare(old_schema, new_schema)

        assert diff.has_changes
        assert "minProperties" in diff.modified_keys

    def test_compare_properties(self):
        """Test comparison of properties section."""
        old_schema = {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
            },
        }
        new_schema = {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
            },
        }

        diff = self.comparator.compare_properties(old_schema, new_schema)

        assert diff.has_changes
        assert "name" in diff.removed_keys

    def test_compare_required(self):
        """Test comparison of required fields."""
        old_schema = {
            "type": "object",
            "required": ["id", "name"],
        }
        new_schema = {
            "type": "object",
            "required": ["id", "name", "email"],
        }

        result = self.comparator.compare_required(old_schema, new_schema)

        assert "email" in result["added"]
        assert len(result["removed"]) == 0

    def test_get_property_diff(self):
        """Test getting diff for specific property."""
        old_schema = {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
            },
        }
        new_schema = {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"},
            },
        }

        diff = self.comparator.get_property_diff(old_schema, new_schema, "id")

        assert diff is not None
        old_value, new_value = diff
        assert old_value["type"] == "string"
        assert new_value["type"] == "integer"

    def test_get_property_diff_unchanged(self):
        """Test getting diff for unchanged property."""
        old_schema = {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
            },
        }
        new_schema = {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
            },
        }

        diff = self.comparator.get_property_diff(old_schema, new_schema, "id")

        assert diff is None

    def test_get_summary(self):
        """Test getting summary of changes."""
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
                "email": {"type": "string"},
            },
            "required": ["id", "email"],
        }

        summary = self.comparator.get_summary(old_schema, new_schema)

        assert summary["has_changes"] is True
        assert summary["total_changes"] > 0
        assert "top_level_changes" in summary
        assert "property_changes" in summary
        assert "required_changes" in summary

    def test_schema_diff_string_representation(self):
        """Test schema diff string representation."""
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

        # Compare properties directly to see added keys
        diff = self.comparator.compare_properties(old_schema, new_schema)

        diff_str = str(diff)
        assert "Schema Diff" in diff_str
        assert "Added" in diff_str
        assert "name" in diff.added_keys

    def test_all_changes_property(self):
        """Test all_changes property."""
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
            "required": ["id"],
        }

        diff = self.comparator.compare(old_schema, new_schema)

        all_changes = diff.all_changes
        assert len(all_changes) > 0
        # Check that keys are prefixed with +, -, or ~
        for key in all_changes.keys():
            assert key[0] in ("+", "-", "~")

    def test_compare_complex_schemas(self):
        """Test comparison of complex nested schemas."""
        old_schema = {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "profile": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "age": {"type": "integer"},
                            },
                        },
                    },
                },
            },
        }
        new_schema = {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "profile": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                            },
                        },
                    },
                },
            },
        }

        diff = self.comparator.compare(old_schema, new_schema)

        # The comparison is at top level, so it should show modification
        assert diff.has_changes or len(diff.modified_keys) > 0
