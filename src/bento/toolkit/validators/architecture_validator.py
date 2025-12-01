#!/usr/bin/env python3
"""Bento Framework Architecture Validation Tool.

This tool validates that the codebase follows Bento Framework architectural standards:
- Proper layering (Domain/Application/Infrastructure)
- Correct dependency directions
- Standard ApplicationService patterns
- UnitOfWork usage compliance
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any


class ArchitectureValidator:
    """Validates Bento Framework architecture compliance."""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.violations: list[str] = []

    def validate_all(self) -> dict[str, Any]:
        """Run all architecture validations.

        Returns:
            Validation report with violations and recommendations
        """
        print("🔍 Starting Bento Framework Architecture Validation")
        print("=" * 55)

        # Clear previous violations
        self.violations = []

        # Run validation checks
        self._validate_layer_dependencies()
        self._validate_application_services()
        self._validate_domain_purity()
        self._validate_uow_usage()

        # Generate report
        report = {
            "total_violations": len(self.violations),
            "violations": self.violations,
            "compliance_score": self._calculate_compliance_score(),
            "recommendations": self._generate_recommendations(),
        }

        self._print_report(report)
        return report

    def _validate_layer_dependencies(self):
        """Validate that layers follow dependency inversion principle."""
        print("\n📋 Checking Layer Dependencies...")

        # Domain layer should not depend on Application/Infrastructure
        domain_files = self._find_python_files("src/bento/domain")
        for file_path in domain_files:
            violations = self._check_domain_dependencies(file_path)
            self.violations.extend(violations)

        # Application layer should not depend on Infrastructure concrete classes
        app_files = self._find_python_files("src/bento/application")
        for file_path in app_files:
            violations = self._check_application_dependencies(file_path)
            self.violations.extend(violations)

        print(
            f"   Found {len([v for v in self.violations if 'dependency' in v.lower()])} dependency violations"
        )

    def _validate_application_services(self):
        """Validate ApplicationService patterns."""
        print("\n🏗️ Checking ApplicationService Patterns...")

        # Find all ApplicationService classes
        app_services = self._find_application_services()

        for service_path, service_class in app_services:
            violations = self._check_application_service_pattern(service_path, service_class)
            self.violations.extend(violations)

        print(f"   Checked {len(app_services)} ApplicationServices")

    def _validate_domain_purity(self):
        """Validate Domain layer purity (no infrastructure concerns)."""
        print("\n🎯 Checking Domain Layer Purity...")

        domain_files = self._find_python_files("src/bento/domain")
        infrastructure_imports = [
            "sqlalchemy",
            "redis",
            "kafka",
            "pulsar",
            "requests",
            "bento.persistence",
            "bento.infrastructure",
            "bento.adapters",
        ]

        for file_path in domain_files:
            content = self._read_file(file_path)
            for imp in infrastructure_imports:
                if f"import {imp}" in content or f"from {imp}" in content:
                    self.violations.append(f"Domain purity violation: {file_path} imports {imp}")

        domain_violations = len([v for v in self.violations if "Domain purity" in v])
        print(f"   Found {domain_violations} domain purity violations")

    def _validate_uow_usage(self):
        """Validate UnitOfWork usage patterns."""
        print("\n🔄 Checking UnitOfWork Usage...")

        app_files = self._find_python_files("src/bento/application")

        for file_path in app_files:
            if "service" in file_path.name.lower():
                violations = self._check_uow_patterns(file_path)
                self.violations.extend(violations)

        uow_violations = len([v for v in self.violations if "UoW" in v])
        print(f"   Found {uow_violations} UoW pattern violations")

    def _check_domain_dependencies(self, file_path: Path) -> list[str]:
        """Check if domain file has invalid dependencies."""
        violations = []
        content = self._read_file(file_path)

        # Forbidden imports for Domain layer
        forbidden_patterns = [
            "from bento.application",
            "from bento.infrastructure",
            "from bento.persistence.uow",
            "from bento.adapters",
            "import sqlalchemy",
            "import redis",
        ]

        for pattern in forbidden_patterns:
            if pattern in content:
                violations.append(
                    f"Domain dependency violation: {file_path.relative_to(self.project_root)} "
                    f"contains forbidden import '{pattern}'"
                )

        return violations

    def _check_application_dependencies(self, file_path: Path) -> list[str]:
        """Check if application file has invalid dependencies."""
        violations = []
        content = self._read_file(file_path)

        # Application layer should not import concrete infrastructure
        forbidden_patterns = [
            "from bento.adapters.messaging.pulsar",
            "from bento.adapters.messaging.inprocess",
            "from bento.infrastructure.database",
            "from bento.persistence.repository.sqlalchemy",
        ]

        for pattern in forbidden_patterns:
            if pattern in content:
                violations.append(
                    f"Application dependency violation: {file_path.relative_to(self.project_root)} "
                    f"imports concrete implementation '{pattern}'"
                )

        return violations

    def _find_application_services(self) -> list[tuple[Path, str]]:
        """Find all ApplicationService classes."""
        services = []
        app_files = self._find_python_files("src/bento/application")

        for file_path in app_files:
            if "service" in file_path.name.lower():
                content = self._read_file(file_path)

                # Parse AST to find class definitions
                try:
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            if "Service" in node.name:
                                services.append((file_path, node.name))
                except SyntaxError:
                    continue

        return services

    def _check_application_service_pattern(self, file_path: Path, class_name: str) -> list[str]:
        """Check if ApplicationService follows standard pattern."""
        violations = []
        content = self._read_file(file_path)

        # Must have UnitOfWork dependency
        if "uow: UnitOfWork" not in content and "uow:" not in content:
            violations.append(
                f"ApplicationService pattern violation: {class_name} in {file_path.name} "
                f"must have UnitOfWork dependency"
            )

        # Should use transaction boundary
        if "async with" not in content and "Service" in class_name:
            violations.append(
                f"ApplicationService pattern violation: {class_name} should use "
                f"'async with uow:' transaction boundary"
            )

        # Should call uow.commit()
        if "uow.commit()" not in content and "Service" in class_name:
            violations.append(
                f"ApplicationService pattern violation: {class_name} should call "
                f"uow.commit() to persist changes"
            )

        return violations

    def _check_uow_patterns(self, file_path: Path) -> list[str]:
        """Check UnitOfWork usage patterns."""
        violations = []
        content = self._read_file(file_path)

        # If file uses Repository, it should be through UoW
        if "Repository" in content and "uow.repository(" not in content:
            if "def __init__" in content and "repository:" in content:
                violations.append(
                    f"UoW pattern violation: {file_path.name} directly injects Repository. "
                    f"Should use uow.repository() instead"
                )

        return violations

    def _find_python_files(self, directory: str) -> list[Path]:
        """Find all Python files in directory."""
        dir_path = self.project_root / directory
        if not dir_path.exists():
            return []

        return list(dir_path.rglob("*.py"))

    def _read_file(self, file_path: Path) -> str:
        """Read file content safely."""
        try:
            with open(file_path, encoding="utf-8") as f:
                return f.read()
        except Exception:
            return ""

    def _calculate_compliance_score(self) -> float:
        """Calculate architecture compliance score (0-100)."""
        total_files = len(list(self.project_root.rglob("*.py")))
        if total_files == 0:
            return 100.0

        # Deduct points for violations
        penalty_per_violation = 2.0
        score = 100.0 - (len(self.violations) * penalty_per_violation)

        return max(0.0, min(100.0, score))

    def _generate_recommendations(self) -> list[str]:
        """Generate recommendations based on violations."""
        recommendations = []

        dependency_violations = [v for v in self.violations if "dependency" in v.lower()]
        if dependency_violations:
            recommendations.append(
                "🔧 Fix dependency violations by removing forbidden imports from Domain layer"
            )

        service_violations = [v for v in self.violations if "ApplicationService" in v]
        if service_violations:
            recommendations.append(
                "🏗️ Update ApplicationServices to use StandardApplicationService base class"
            )

        uow_violations = [v for v in self.violations if "UoW" in v]
        if uow_violations:
            recommendations.append(
                "🔄 Refactor Repository access to use UnitOfWork pattern: uow.repository(Type)"
            )

        purity_violations = [v for v in self.violations if "purity" in v.lower()]
        if purity_violations:
            recommendations.append("🎯 Remove infrastructure dependencies from Domain layer")

        return recommendations

    def _print_report(self, report: dict[str, Any]):
        """Print validation report."""
        print("\n📊 Architecture Validation Report")
        print("=" * 40)

        score = report["compliance_score"]
        print(f"🎯 Compliance Score: {score:.1f}/100")

        if score >= 90:
            print("✅ Excellent architecture compliance!")
        elif score >= 75:
            print("⚠️  Good compliance with room for improvement")
        else:
            print("❌ Architecture needs significant improvements")

        print(f"\n📋 Violations Found: {report['total_violations']}")

        if report["violations"]:
            print("\nDetailed Violations:")
            for i, violation in enumerate(report["violations"], 1):
                print(f"   {i}. {violation}")

        if report["recommendations"]:
            print("\n💡 Recommendations:")
            for rec in report["recommendations"]:
                print(f"   {rec}")

        print("\n🎯 Next Steps:")
        if report["total_violations"] == 0:
            print("   🎉 Architecture is compliant! Consider adding new features or optimizations.")
        elif report["total_violations"] <= 5:
            print("   🔧 Fix the few remaining violations for perfect compliance.")
        else:
            print("   📋 Focus on high-priority violations first, then address remaining issues.")


def main():
    """Main entry point for architecture validation."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate Bento Framework architecture")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    parser.add_argument("--output", help="Output report to file")

    args = parser.parse_args()

    # Run validation
    validator = ArchitectureValidator(args.project_root)
    report = validator.validate_all()

    # Save report if requested
    if args.output:
        import json

        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n📄 Report saved to: {args.output}")

    # Exit with error code if violations found
    exit_code = min(report["total_violations"], 10)  # Cap at 10
    exit(exit_code)


if __name__ == "__main__":
    main()
