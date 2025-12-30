"""Schema Comparator - Contracts-as-Code.

Compares two JSON schemas and provides detailed diff information.
Supports loading schemas from files and comparing versions.

Example:
    ```python
    comparator = SchemaComparator()

    # Compare from files
    diff = comparator.compare_files(
        old_path="OrderCreated.v1.schema.json",
        new_path="OrderCreated.v2.schema.json"
    )

    # Or compare dictionaries
    diff = comparator.compare(old_schema, new_schema)
    ```
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SchemaDiff:
    """Represents differences between two schemas.

    Attributes:
        old_schema: Old schema definition
        new_schema: New schema definition
        added_keys: Keys added in new schema
        removed_keys: Keys removed from old schema
        modified_keys: Keys with different values
        all_changes: All changes (added + removed + modified)
    """
    old_schema: dict[str, Any]
    new_schema: dict[str, Any]
    added_keys: dict[str, Any] = field(default_factory=dict)
    removed_keys: dict[str, Any] = field(default_factory=dict)
    modified_keys: dict[str, tuple[Any, Any]] = field(default_factory=dict)

    @property
    def all_changes(self) -> dict[str, Any]:
        """Get all changes as a single dict."""
        result = {}
        for key, value in self.added_keys.items():
            result[f"+{key}"] = value
        for key, value in self.removed_keys.items():
            result[f"-{key}"] = value
        for key, (old, new) in self.modified_keys.items():
            result[f"~{key}"] = {"old": old, "new": new}
        return result

    @property
    def has_changes(self) -> bool:
        """Check if there are any changes."""
        return bool(self.added_keys or self.removed_keys or self.modified_keys)

    def __str__(self) -> str:
        lines = ["Schema Diff:"]
        if self.added_keys:
            lines.append(f"  Added ({len(self.added_keys)}):")
            for key in self.added_keys:
                lines.append(f"    + {key}")
        if self.removed_keys:
            lines.append(f"  Removed ({len(self.removed_keys)}):")
            for key in self.removed_keys:
                lines.append(f"    - {key}")
        if self.modified_keys:
            lines.append(f"  Modified ({len(self.modified_keys)}):")
            for key in self.modified_keys:
                lines.append(f"    ~ {key}")
        return "\n".join(lines)


class SchemaComparator:
    """Compares two JSON schemas and provides diff information.

    Example:
        ```python
        comparator = SchemaComparator()
        diff = comparator.compare(old_schema, new_schema)

        if diff.has_changes:
            print(f"Added: {list(diff.added_keys.keys())}")
            print(f"Removed: {list(diff.removed_keys.keys())}")
            print(f"Modified: {list(diff.modified_keys.keys())}")
        ```
    """

    def compare(
        self,
        old_schema: dict[str, Any],
        new_schema: dict[str, Any],
    ) -> SchemaDiff:
        """Compare two schemas.

        Args:
            old_schema: Old schema definition
            new_schema: New schema definition

        Returns:
            SchemaDiff with comparison results
        """
        diff = SchemaDiff(old_schema=old_schema, new_schema=new_schema)

        # Compare top-level keys
        old_keys = set(old_schema.keys())
        new_keys = set(new_schema.keys())

        # Find added keys
        for key in new_keys - old_keys:
            diff.added_keys[key] = new_schema[key]

        # Find removed keys
        for key in old_keys - new_keys:
            diff.removed_keys[key] = old_schema[key]

        # Find modified keys
        for key in old_keys & new_keys:
            old_value = old_schema[key]
            new_value = new_schema[key]
            if old_value != new_value:
                diff.modified_keys[key] = (old_value, new_value)

        return diff

    def compare_files(
        self,
        old_path: str | pathlib.Path,
        new_path: str | pathlib.Path,
    ) -> SchemaDiff:
        """Compare schemas from files.

        Args:
            old_path: Path to old schema file
            new_path: Path to new schema file

        Returns:
            SchemaDiff with comparison results

        Raises:
            FileNotFoundError: If files don't exist
            json.JSONDecodeError: If files are not valid JSON
        """
        old_path = pathlib.Path(old_path)
        new_path = pathlib.Path(new_path)

        if not old_path.exists():
            raise FileNotFoundError(f"Old schema file not found: {old_path}")
        if not new_path.exists():
            raise FileNotFoundError(f"New schema file not found: {new_path}")

        old_schema = json.loads(old_path.read_text(encoding="utf-8"))
        new_schema = json.loads(new_path.read_text(encoding="utf-8"))

        return self.compare(old_schema, new_schema)

    def compare_properties(
        self,
        old_schema: dict[str, Any],
        new_schema: dict[str, Any],
    ) -> SchemaDiff:
        """Compare properties section of schemas.

        Args:
            old_schema: Old schema definition
            new_schema: New schema definition

        Returns:
            SchemaDiff comparing properties only
        """
        old_props = old_schema.get("properties", {})
        new_props = new_schema.get("properties", {})

        return self.compare(old_props, new_props)

    def compare_required(
        self,
        old_schema: dict[str, Any],
        new_schema: dict[str, Any],
    ) -> dict[str, list[str]]:
        """Compare required fields between schemas.

        Args:
            old_schema: Old schema definition
            new_schema: New schema definition

        Returns:
            Dict with 'added', 'removed' required fields
        """
        old_required = set(old_schema.get("required", []))
        new_required = set(new_schema.get("required", []))

        return {
            "added": sorted(new_required - old_required),
            "removed": sorted(old_required - new_required),
        }

    def get_property_diff(
        self,
        old_schema: dict[str, Any],
        new_schema: dict[str, Any],
        property_name: str,
    ) -> tuple[Any, Any] | None:
        """Get diff for a specific property.

        Args:
            old_schema: Old schema definition
            new_schema: New schema definition
            property_name: Name of property to compare

        Returns:
            Tuple of (old_value, new_value) or None if property unchanged
        """
        old_props = old_schema.get("properties", {})
        new_props = new_schema.get("properties", {})

        old_value = old_props.get(property_name)
        new_value = new_props.get(property_name)

        if old_value == new_value:
            return None

        return (old_value, new_value)

    def get_summary(
        self,
        old_schema: dict[str, Any],
        new_schema: dict[str, Any],
    ) -> dict[str, Any]:
        """Get summary of schema changes.

        Args:
            old_schema: Old schema definition
            new_schema: New schema definition

        Returns:
            Summary dict with change statistics
        """
        diff = self.compare(old_schema, new_schema)
        props_diff = self.compare_properties(old_schema, new_schema)
        required_diff = self.compare_required(old_schema, new_schema)

        return {
            "total_changes": len(diff.all_changes),
            "top_level_changes": {
                "added": len(diff.added_keys),
                "removed": len(diff.removed_keys),
                "modified": len(diff.modified_keys),
            },
            "property_changes": {
                "added": len(props_diff.added_keys),
                "removed": len(props_diff.removed_keys),
                "modified": len(props_diff.modified_keys),
            },
            "required_changes": {
                "added": len(required_diff["added"]),
                "removed": len(required_diff["removed"]),
            },
            "has_changes": diff.has_changes,
        }
