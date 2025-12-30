"""Breaking Change Detector - Contracts-as-Code.

Detects breaking changes between schema versions and validates compatibility.
Uses JSON Schema comparison to identify incompatible changes.

Example:
    ```python
    detector = BreakingChangeDetector()

    # Detect breaking changes between versions
    changes = detector.detect(
        old_schema={"type": "object", "properties": {"id": {"type": "string"}}},
        new_schema={"type": "object", "properties": {"id": {"type": "integer"}}}
    )

    # Check if changes are breaking
    for change in changes:
        if change.is_breaking:
            print(f"Breaking: {change.description}")
    ```
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ChangeType(Enum):
    """Type of schema change."""
    PROPERTY_ADDED = "property_added"
    PROPERTY_REMOVED = "property_removed"
    PROPERTY_TYPE_CHANGED = "property_type_changed"
    PROPERTY_REQUIRED_CHANGED = "property_required_changed"
    ENUM_VALUE_REMOVED = "enum_value_removed"
    ENUM_VALUE_ADDED = "enum_value_added"
    PATTERN_CHANGED = "pattern_changed"
    MIN_LENGTH_INCREASED = "min_length_increased"
    MAX_LENGTH_DECREASED = "max_length_decreased"
    MIN_VALUE_INCREASED = "min_value_increased"
    MAX_VALUE_DECREASED = "max_value_decreased"
    ADDITIONAL_PROPERTIES_CHANGED = "additional_properties_changed"
    ARRAY_ITEMS_CHANGED = "array_items_changed"
    SCHEMA_STRUCTURE_CHANGED = "schema_structure_changed"


@dataclass
class BreakingChange:
    """Represents a breaking change in schema.

    Attributes:
        change_type: Type of change (ChangeType enum)
        path: JSON path to the changed property (e.g., "properties.id")
        description: Human-readable description of the change
        is_breaking: Whether this change breaks compatibility
        severity: Severity level (critical, major, minor)
        old_value: Old schema value
        new_value: New schema value
        migration_hint: Suggested migration path
    """
    change_type: ChangeType
    path: str
    description: str
    is_breaking: bool
    severity: str = "major"
    old_value: Any = None
    new_value: Any = None
    migration_hint: str = ""

    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.description} (path: {self.path})"


@dataclass
class BreakingChangeReport:
    """Report of all breaking changes detected.

    Attributes:
        old_version: Version of old schema
        new_version: Version of new schema
        breaking_changes: List of breaking changes
        compatible_changes: List of compatible changes
        is_compatible: Whether schemas are compatible
    """
    old_version: str
    new_version: str
    breaking_changes: list[BreakingChange] = field(default_factory=list)
    compatible_changes: list[BreakingChange] = field(default_factory=list)

    @property
    def is_compatible(self) -> bool:
        """Check if schemas are compatible."""
        return len(self.breaking_changes) == 0

    @property
    def total_changes(self) -> int:
        """Total number of changes."""
        return len(self.breaking_changes) + len(self.compatible_changes)

    def __str__(self) -> str:
        lines = [
            f"Breaking Change Report: {self.old_version} → {self.new_version}",
            f"Compatible: {self.is_compatible}",
            f"Breaking Changes: {len(self.breaking_changes)}",
            f"Compatible Changes: {len(self.compatible_changes)}",
        ]
        if self.breaking_changes:
            lines.append("\nBreaking Changes:")
            for change in self.breaking_changes:
                lines.append(f"  - {change}")
        if self.compatible_changes:
            lines.append("\nCompatible Changes:")
            for change in self.compatible_changes:
                lines.append(f"  - {change}")
        return "\n".join(lines)


class BreakingChangeDetector:
    """Detects breaking changes between schema versions.

    Compares two JSON schemas and identifies changes that would break
    compatibility with existing clients/consumers.

    Example:
        ```python
        detector = BreakingChangeDetector()
        report = detector.detect(old_schema, new_schema)

        if not report.is_compatible:
            print(f"Found {len(report.breaking_changes)} breaking changes")
            for change in report.breaking_changes:
                print(f"  - {change.description}")
        ```
    """

    def detect(
        self,
        old_schema: dict[str, Any],
        new_schema: dict[str, Any],
        old_version: str = "old",
        new_version: str = "new",
    ) -> BreakingChangeReport:
        """Detect breaking changes between two schemas.

        Args:
            old_schema: Old schema definition
            new_schema: New schema definition
            old_version: Version label for old schema
            new_version: Version label for new schema

        Returns:
            BreakingChangeReport with detected changes
        """
        report = BreakingChangeReport(
            old_version=old_version,
            new_version=new_version,
        )

        # Compare schemas recursively
        self._compare_schemas(
            old_schema,
            new_schema,
            path="",
            report=report,
        )

        return report

    def _compare_schemas(
        self,
        old: dict[str, Any],
        new: dict[str, Any],
        path: str,
        report: BreakingChangeReport,
    ) -> None:
        """Recursively compare schemas."""
        # Check type changes
        old_type = old.get("type")
        new_type = new.get("type")
        if old_type != new_type:
            change = BreakingChange(
                change_type=ChangeType.PROPERTY_TYPE_CHANGED,
                path=path or "root",
                description=f"Type changed from {old_type} to {new_type}",
                is_breaking=True,
                severity="critical",
                old_value=old_type,
                new_value=new_type,
                migration_hint=f"Update client to handle {new_type} type",
            )
            report.breaking_changes.append(change)
            return

        # Handle object type
        if old_type == "object":
            self._compare_object_schemas(old, new, path, report)

        # Handle array type
        elif old_type == "array":
            self._compare_array_schemas(old, new, path, report)

        # Handle string type
        elif old_type == "string":
            self._compare_string_schemas(old, new, path, report)

        # Handle number/integer types
        elif old_type in ("number", "integer"):
            self._compare_numeric_schemas(old, new, path, report)

        # Handle enum
        if "enum" in old or "enum" in new:
            self._compare_enum_schemas(old, new, path, report)

    def _compare_object_schemas(
        self,
        old: dict[str, Any],
        new: dict[str, Any],
        path: str,
        report: BreakingChangeReport,
    ) -> None:
        """Compare object schemas."""
        old_props = old.get("properties", {})
        new_props = new.get("properties", {})
        old_required = set(old.get("required", []))
        new_required = set(new.get("required", []))

        # Check for removed properties
        for prop in old_props:
            if prop not in new_props:
                change = BreakingChange(
                    change_type=ChangeType.PROPERTY_REMOVED,
                    path=f"{path}.{prop}" if path else prop,
                    description=f"Property '{prop}' was removed",
                    is_breaking=True,
                    severity="critical",
                    old_value=old_props[prop],
                    migration_hint=f"Add '{prop}' back or update clients to handle missing property",
                )
                report.breaking_changes.append(change)
            else:
                # Recursively compare property schemas
                prop_path = f"{path}.{prop}" if path else prop
                self._compare_schemas(
                    old_props[prop],
                    new_props[prop],
                    path=prop_path,
                    report=report,
                )

        # Check for added properties
        for prop in new_props:
            if prop not in old_props:
                is_breaking = prop in new_required
                change = BreakingChange(
                    change_type=ChangeType.PROPERTY_ADDED,
                    path=f"{path}.{prop}" if path else prop,
                    description=f"Property '{prop}' was added" +
                                (" (required)" if is_breaking else ""),
                    is_breaking=is_breaking,
                    severity="critical" if is_breaking else "minor",
                    new_value=new_props[prop],
                    migration_hint=f"Provide value for required property '{prop}'" if is_breaking else "",
                )
                if is_breaking:
                    report.breaking_changes.append(change)
                else:
                    report.compatible_changes.append(change)

        # Check for required changes
        newly_required = new_required - old_required
        if newly_required:
            for prop in newly_required:
                change = BreakingChange(
                    change_type=ChangeType.PROPERTY_REQUIRED_CHANGED,
                    path=f"{path}.{prop}" if path else prop,
                    description=f"Property '{prop}' is now required",
                    is_breaking=True,
                    severity="critical",
                    migration_hint=f"Provide value for newly required property '{prop}'",
                )
                report.breaking_changes.append(change)

        # Check additionalProperties change
        old_additional = old.get("additionalProperties", True)
        new_additional = new.get("additionalProperties", True)
        if old_additional is True and new_additional is False:
            change = BreakingChange(
                change_type=ChangeType.ADDITIONAL_PROPERTIES_CHANGED,
                path=path or "root",
                description="additionalProperties changed from true to false",
                is_breaking=True,
                severity="major",
                old_value=old_additional,
                new_value=new_additional,
                migration_hint="Remove any additional properties from objects",
            )
            report.breaking_changes.append(change)

    def _compare_array_schemas(
        self,
        old: dict[str, Any],
        new: dict[str, Any],
        path: str,
        report: BreakingChangeReport,
    ) -> None:
        """Compare array schemas."""
        old_items = old.get("items", {})
        new_items = new.get("items", {})

        if old_items and new_items:
            items_path = f"{path}[*]" if path else "[*]"
            self._compare_schemas(old_items, new_items, items_path, report)

        # Check minItems change
        old_min = old.get("minItems", 0)
        new_min = new.get("minItems", 0)
        if new_min > old_min:
            change = BreakingChange(
                change_type=ChangeType.MIN_LENGTH_INCREASED,
                path=path or "root",
                description=f"minItems increased from {old_min} to {new_min}",
                is_breaking=True,
                severity="major",
                old_value=old_min,
                new_value=new_min,
                migration_hint=f"Ensure arrays have at least {new_min} items",
            )
            report.breaking_changes.append(change)

    def _compare_string_schemas(
        self,
        old: dict[str, Any],
        new: dict[str, Any],
        path: str,
        report: BreakingChangeReport,
    ) -> None:
        """Compare string schemas."""
        # Check minLength change
        old_min = old.get("minLength", 0)
        new_min = new.get("minLength", 0)
        if new_min > old_min:
            change = BreakingChange(
                change_type=ChangeType.MIN_LENGTH_INCREASED,
                path=path or "root",
                description=f"minLength increased from {old_min} to {new_min}",
                is_breaking=True,
                severity="major",
                old_value=old_min,
                new_value=new_min,
                migration_hint=f"Ensure strings have at least {new_min} characters",
            )
            report.breaking_changes.append(change)

        # Check maxLength change
        old_max = old.get("maxLength")
        new_max = new.get("maxLength")
        if old_max is not None and new_max is not None and new_max < old_max:
            change = BreakingChange(
                change_type=ChangeType.MAX_LENGTH_DECREASED,
                path=path or "root",
                description=f"maxLength decreased from {old_max} to {new_max}",
                is_breaking=True,
                severity="major",
                old_value=old_max,
                new_value=new_max,
                migration_hint=f"Ensure strings have at most {new_max} characters",
            )
            report.breaking_changes.append(change)

        # Check pattern change
        old_pattern = old.get("pattern")
        new_pattern = new.get("pattern")
        if old_pattern != new_pattern and new_pattern:
            change = BreakingChange(
                change_type=ChangeType.PATTERN_CHANGED,
                path=path or "root",
                description=f"Pattern changed from '{old_pattern}' to '{new_pattern}'",
                is_breaking=True,
                severity="major",
                old_value=old_pattern,
                new_value=new_pattern,
                migration_hint=f"Ensure strings match pattern: {new_pattern}",
            )
            report.breaking_changes.append(change)

    def _compare_numeric_schemas(
        self,
        old: dict[str, Any],
        new: dict[str, Any],
        path: str,
        report: BreakingChangeReport,
    ) -> None:
        """Compare numeric schemas."""
        # Check minimum change
        old_min = old.get("minimum")
        new_min = new.get("minimum")
        if old_min is not None and new_min is not None and new_min > old_min:
            change = BreakingChange(
                change_type=ChangeType.MIN_VALUE_INCREASED,
                path=path or "root",
                description=f"minimum increased from {old_min} to {new_min}",
                is_breaking=True,
                severity="major",
                old_value=old_min,
                new_value=new_min,
                migration_hint=f"Ensure values are >= {new_min}",
            )
            report.breaking_changes.append(change)

        # Check maximum change
        old_max = old.get("maximum")
        new_max = new.get("maximum")
        if old_max is not None and new_max is not None and new_max < old_max:
            change = BreakingChange(
                change_type=ChangeType.MAX_VALUE_DECREASED,
                path=path or "root",
                description=f"maximum decreased from {old_max} to {new_max}",
                is_breaking=True,
                severity="major",
                old_value=old_max,
                new_value=new_max,
                migration_hint=f"Ensure values are <= {new_max}",
            )
            report.breaking_changes.append(change)

    def _compare_enum_schemas(
        self,
        old: dict[str, Any],
        new: dict[str, Any],
        path: str,
        report: BreakingChangeReport,
    ) -> None:
        """Compare enum schemas."""
        old_enum = set(old.get("enum", []))
        new_enum = set(new.get("enum", []))

        # Check for removed enum values
        removed = old_enum - new_enum
        for value in removed:
            change = BreakingChange(
                change_type=ChangeType.ENUM_VALUE_REMOVED,
                path=path or "root",
                description=f"Enum value '{value}' was removed",
                is_breaking=True,
                severity="critical",
                old_value=value,
                migration_hint=f"Update clients to not use '{value}'",
            )
            report.breaking_changes.append(change)

        # Check for added enum values
        added = new_enum - old_enum
        for value in added:
            change = BreakingChange(
                change_type=ChangeType.ENUM_VALUE_ADDED,
                path=path or "root",
                description=f"Enum value '{value}' was added",
                is_breaking=False,
                severity="minor",
                new_value=value,
            )
            report.compatible_changes.append(change)
