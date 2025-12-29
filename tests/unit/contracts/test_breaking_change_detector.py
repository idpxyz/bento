"""Tests for BreakingChangeDetector."""

from bento.contracts.breaking_change_detector import (
    BreakingChangeDetector,
    ChangeType,
)


class TestBreakingChangeDetector:
    """Test breaking change detection."""

    def setup_method(self):
        """Set up test fixtures."""
        self.detector = BreakingChangeDetector()

    def test_detect_property_removed(self):
        """Test detection of removed property."""
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

        report = self.detector.detect(old_schema, new_schema)

        assert not report.is_compatible
        assert len(report.breaking_changes) == 1
        assert report.breaking_changes[0].change_type == ChangeType.PROPERTY_REMOVED
        assert "name" in report.breaking_changes[0].description

    def test_detect_property_type_changed(self):
        """Test detection of property type change."""
        old_schema = {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
            },
        }
        new_schema = {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
            },
        }

        report = self.detector.detect(old_schema, new_schema)

        assert not report.is_compatible
        assert len(report.breaking_changes) == 1
        assert report.breaking_changes[0].change_type == ChangeType.PROPERTY_TYPE_CHANGED

    def test_detect_required_field_added(self):
        """Test detection of newly required field."""
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

        report = self.detector.detect(old_schema, new_schema)

        assert not report.is_compatible
        assert len(report.breaking_changes) == 1
        assert report.breaking_changes[0].change_type == ChangeType.PROPERTY_REQUIRED_CHANGED

    def test_detect_enum_value_removed(self):
        """Test detection of removed enum value."""
        old_schema = {
            "type": "string",
            "enum": ["DRAFT", "SUBMITTED", "COMPLETED"],
        }
        new_schema = {
            "type": "string",
            "enum": ["DRAFT", "SUBMITTED"],
        }

        report = self.detector.detect(old_schema, new_schema)

        assert not report.is_compatible
        assert len(report.breaking_changes) == 1
        assert report.breaking_changes[0].change_type == ChangeType.ENUM_VALUE_REMOVED

    def test_detect_enum_value_added(self):
        """Test detection of added enum value (compatible)."""
        old_schema = {
            "type": "string",
            "enum": ["DRAFT", "SUBMITTED"],
        }
        new_schema = {
            "type": "string",
            "enum": ["DRAFT", "SUBMITTED", "COMPLETED"],
        }

        report = self.detector.detect(old_schema, new_schema)

        assert report.is_compatible
        assert len(report.compatible_changes) == 1
        assert report.compatible_changes[0].change_type == ChangeType.ENUM_VALUE_ADDED

    def test_detect_min_length_increased(self):
        """Test detection of increased minLength."""
        old_schema = {
            "type": "string",
            "minLength": 1,
        }
        new_schema = {
            "type": "string",
            "minLength": 5,
        }

        report = self.detector.detect(old_schema, new_schema)

        assert not report.is_compatible
        assert len(report.breaking_changes) == 1
        assert report.breaking_changes[0].change_type == ChangeType.MIN_LENGTH_INCREASED

    def test_detect_max_length_decreased(self):
        """Test detection of decreased maxLength."""
        old_schema = {
            "type": "string",
            "maxLength": 100,
        }
        new_schema = {
            "type": "string",
            "maxLength": 50,
        }

        report = self.detector.detect(old_schema, new_schema)

        assert not report.is_compatible
        assert len(report.breaking_changes) == 1
        assert report.breaking_changes[0].change_type == ChangeType.MAX_LENGTH_DECREASED

    def test_detect_pattern_changed(self):
        """Test detection of pattern change."""
        old_schema = {
            "type": "string",
            "pattern": "^[a-z]+$",
        }
        new_schema = {
            "type": "string",
            "pattern": "^[a-z0-9]+$",
        }

        report = self.detector.detect(old_schema, new_schema)

        assert not report.is_compatible
        assert len(report.breaking_changes) == 1
        assert report.breaking_changes[0].change_type == ChangeType.PATTERN_CHANGED

    def test_detect_additional_properties_restricted(self):
        """Test detection of additionalProperties restriction."""
        old_schema = {
            "type": "object",
            "additionalProperties": True,
        }
        new_schema = {
            "type": "object",
            "additionalProperties": False,
        }

        report = self.detector.detect(old_schema, new_schema)

        assert not report.is_compatible
        assert len(report.breaking_changes) == 1
        assert (
            report.breaking_changes[0].change_type
            == ChangeType.ADDITIONAL_PROPERTIES_CHANGED
        )

    def test_detect_multiple_changes(self):
        """Test detection of multiple changes."""
        old_schema = {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
                "status": {"type": "string", "enum": ["DRAFT", "ACTIVE"]},
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

        report = self.detector.detect(old_schema, new_schema)

        assert not report.is_compatible
        assert len(report.breaking_changes) >= 2

    def test_report_string_representation(self):
        """Test breaking change report string representation."""
        old_schema = {
            "type": "object",
            "properties": {"id": {"type": "string"}},
        }
        new_schema = {
            "type": "object",
            "properties": {},
        }

        report = self.detector.detect(old_schema, new_schema, "v1", "v2")

        report_str = str(report)
        assert "v1" in report_str
        assert "v2" in report_str
        assert "Breaking Change Report" in report_str

    def test_change_severity_levels(self):
        """Test that changes have appropriate severity levels."""
        old_schema = {
            "type": "object",
            "properties": {"id": {"type": "string"}},
        }
        new_schema = {
            "type": "object",
            "properties": {},
        }

        report = self.detector.detect(old_schema, new_schema)

        for change in report.breaking_changes:
            assert change.severity in ("critical", "major", "minor")

    def test_nested_object_comparison(self):
        """Test comparison of nested objects."""
        old_schema = {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                    },
                }
            },
        }
        new_schema = {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                    },
                }
            },
        }

        report = self.detector.detect(old_schema, new_schema)

        assert not report.is_compatible
        # Should detect removal of nested property
        assert any("name" in str(c) for c in report.breaking_changes)

    def test_array_items_change(self):
        """Test detection of array items change."""
        old_schema = {
            "type": "array",
            "items": {"type": "string"},
        }
        new_schema = {
            "type": "array",
            "items": {"type": "integer"},
        }

        report = self.detector.detect(old_schema, new_schema)

        assert not report.is_compatible

    def test_migration_hints_provided(self):
        """Test that migration hints are provided."""
        old_schema = {
            "type": "object",
            "properties": {"id": {"type": "string"}},
        }
        new_schema = {
            "type": "object",
            "properties": {},
        }

        report = self.detector.detect(old_schema, new_schema)

        for change in report.breaking_changes:
            assert change.migration_hint, "Migration hint should be provided"
