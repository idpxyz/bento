"""Compatibility Validator - Contracts-as-Code.

Validates compatibility between schema versions and provides migration guidance.
Supports forward and backward compatibility checks.

Example:
    ```python
    validator = CompatibilityValidator()

    # Check if new schema is backward compatible
    result = validator.validate_backward_compatible(old_schema, new_schema)
    if result.is_compatible:
        print("Safe to deploy new version")
    else:
        print("Breaking changes detected:")
        for issue in result.issues:
            print(f"  - {issue}")
    ```
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from bento.contracts.breaking_change_detector import BreakingChangeDetector


class CompatibilityMode(Enum):
    """Compatibility check mode."""

    BACKWARD = "backward"  # New schema must accept old data
    FORWARD = "forward"  # Old schema must accept new data
    FULL = "full"  # Both directions


@dataclass
class CompatibilityResult:
    """Result of compatibility validation.

    Attributes:
        is_compatible: Whether schemas are compatible
        mode: Compatibility mode checked
        issues: List of compatibility issues
        breaking_changes: Breaking changes detected
        migration_guide: Suggested migration steps
    """

    is_compatible: bool
    mode: CompatibilityMode
    issues: list[str] = field(default_factory=list)
    breaking_changes: list[str] = field(default_factory=list)
    migration_guide: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        lines = [
            f"Compatibility Result ({self.mode.value}):",
            f"  Compatible: {self.is_compatible}",
        ]
        if self.issues:
            lines.append(f"  Issues ({len(self.issues)}):")
            for issue in self.issues:
                lines.append(f"    - {issue}")
        if self.breaking_changes:
            lines.append(f"  Breaking Changes ({len(self.breaking_changes)}):")
            for change in self.breaking_changes:
                lines.append(f"    - {change}")
        if self.migration_guide:
            lines.append("  Migration Guide:")
            for step in self.migration_guide:
                lines.append(f"    - {step}")
        return "\n".join(lines)


class CompatibilityValidator:
    """Validates compatibility between schema versions.

    Checks if schemas are compatible in specified direction(s) and
    provides migration guidance.

    Example:
        ```python
        validator = CompatibilityValidator()

        # Backward compatibility (new schema accepts old data)
        result = validator.validate_backward_compatible(old, new)

        # Forward compatibility (old schema accepts new data)
        result = validator.validate_forward_compatible(old, new)

        # Full compatibility (both directions)
        result = validator.validate_full_compatible(old, new)
        ```
    """

    def __init__(self):
        """Initialize validator with breaking change detector."""
        self.detector = BreakingChangeDetector()

    def validate_backward_compatible(
        self,
        old_schema: dict[str, Any],
        new_schema: dict[str, Any],
    ) -> CompatibilityResult:
        """Validate backward compatibility.

        New schema must accept all data that old schema accepts.
        Checks if new schema is a superset of old schema.

        Args:
            old_schema: Old schema definition
            new_schema: New schema definition

        Returns:
            CompatibilityResult for backward compatibility
        """
        report = self.detector.detect(old_schema, new_schema)
        result = CompatibilityResult(
            is_compatible=report.is_compatible,
            mode=CompatibilityMode.BACKWARD,
        )

        # Collect breaking changes as issues
        for change in report.breaking_changes:
            result.issues.append(change.description)
            result.breaking_changes.append(change.description)
            if change.migration_hint:
                result.migration_guide.append(change.migration_hint)

        # Additional backward compatibility checks
        self._check_backward_compatibility(old_schema, new_schema, result)

        return result

    def validate_forward_compatible(
        self,
        old_schema: dict[str, Any],
        new_schema: dict[str, Any],
    ) -> CompatibilityResult:
        """Validate forward compatibility.

        Old schema must accept all data that new schema accepts.
        Checks if old schema is a superset of new schema.

        Args:
            old_schema: Old schema definition
            new_schema: New schema definition

        Returns:
            CompatibilityResult for forward compatibility
        """
        # For forward compatibility, reverse the check
        report = self.detector.detect(new_schema, old_schema)
        result = CompatibilityResult(
            is_compatible=report.is_compatible,
            mode=CompatibilityMode.FORWARD,
        )

        # Collect breaking changes as issues
        for change in report.breaking_changes:
            result.issues.append(change.description)
            result.breaking_changes.append(change.description)
            if change.migration_hint:
                result.migration_guide.append(change.migration_hint)

        # Additional forward compatibility checks
        self._check_forward_compatibility(old_schema, new_schema, result)

        return result

    def validate_full_compatible(
        self,
        old_schema: dict[str, Any],
        new_schema: dict[str, Any],
    ) -> CompatibilityResult:
        """Validate full compatibility (both directions).

        Both schemas must be compatible with each other.

        Args:
            old_schema: Old schema definition
            new_schema: New schema definition

        Returns:
            CompatibilityResult for full compatibility
        """
        backward = self.validate_backward_compatible(old_schema, new_schema)
        forward = self.validate_forward_compatible(old_schema, new_schema)

        result = CompatibilityResult(
            is_compatible=backward.is_compatible and forward.is_compatible,
            mode=CompatibilityMode.FULL,
            issues=backward.issues + forward.issues,
            breaking_changes=backward.breaking_changes + forward.breaking_changes,
            migration_guide=backward.migration_guide + forward.migration_guide,
        )

        return result

    def _check_backward_compatibility(
        self,
        old_schema: dict[str, Any],
        new_schema: dict[str, Any],
        result: CompatibilityResult,
    ) -> None:
        """Additional backward compatibility checks."""
        # Check if required fields were added
        old_required = set(old_schema.get("required", []))
        new_required = set(new_schema.get("required", []))
        newly_required = new_required - old_required

        if newly_required:
            result.is_compatible = False
            for field in newly_required:
                issue = f"New required field '{field}' breaks backward compatibility"
                result.issues.append(issue)
                result.breaking_changes.append(issue)
                result.migration_guide.append(
                    f"Provide default value for '{field}' or make it optional"
                )

        # Check if additionalProperties was restricted
        old_additional = old_schema.get("additionalProperties", True)
        new_additional = new_schema.get("additionalProperties", True)

        if old_additional is True and new_additional is False:
            result.is_compatible = False
            issue = "additionalProperties changed from true to false"
            result.issues.append(issue)
            result.breaking_changes.append(issue)
            result.migration_guide.append(
                "Allow additionalProperties or document required properties"
            )

    def _check_forward_compatibility(
        self,
        old_schema: dict[str, Any],
        new_schema: dict[str, Any],
        result: CompatibilityResult,
    ) -> None:
        """Additional forward compatibility checks."""
        # Check if required fields were removed
        old_required = set(old_schema.get("required", []))
        new_required = set(new_schema.get("required", []))
        removed_required = old_required - new_required

        if removed_required:
            # This is actually compatible for forward compatibility
            # (old schema can accept new data without those fields)
            for field in removed_required:
                guide = f"Field '{field}' is no longer required in new version"
                result.migration_guide.append(guide)

        # Check if additionalProperties was expanded
        old_additional = old_schema.get("additionalProperties", True)
        new_additional = new_schema.get("additionalProperties", True)

        if old_additional is False and new_additional is True:
            # This is compatible for forward compatibility
            guide = "New version accepts additional properties"
            result.migration_guide.append(guide)

    def get_compatibility_matrix(
        self,
        schemas: dict[str, dict[str, Any]],
    ) -> dict[str, dict[str, bool]]:
        """Get compatibility matrix for multiple schema versions.

        Args:
            schemas: Dict mapping version to schema definition

        Returns:
            Matrix showing backward compatibility between versions
        """
        versions = sorted(schemas.keys())
        matrix: dict[str, dict[str, bool]] = {}

        for i, old_version in enumerate(versions):
            matrix[old_version] = {}
            for j, new_version in enumerate(versions):
                if i == j:
                    matrix[old_version][new_version] = True
                elif i < j:
                    # Check backward compatibility
                    result = self.validate_backward_compatible(
                        schemas[old_version],
                        schemas[new_version],
                    )
                    matrix[old_version][new_version] = result.is_compatible
                else:
                    # Check forward compatibility
                    result = self.validate_forward_compatible(
                        schemas[old_version],
                        schemas[new_version],
                    )
                    matrix[old_version][new_version] = result.is_compatible

        return matrix

    def get_migration_path(
        self,
        old_schema: dict[str, Any],
        new_schema: dict[str, Any],
    ) -> list[str]:
        """Get suggested migration path from old to new schema.

        Args:
            old_schema: Old schema definition
            new_schema: New schema definition

        Returns:
            List of migration steps
        """
        result = self.validate_backward_compatible(old_schema, new_schema)

        steps = [
            "Migration Path:",
            "1. Review breaking changes above",
        ]

        if result.migration_guide:
            steps.append("2. Apply migration steps:")
            for i, guide in enumerate(result.migration_guide, 1):
                steps.append(f"   {i}. {guide}")

        steps.extend(
            [
                "3. Update clients to handle new schema",
                "4. Deploy new version",
                "5. Monitor for compatibility issues",
            ]
        )

        return steps
