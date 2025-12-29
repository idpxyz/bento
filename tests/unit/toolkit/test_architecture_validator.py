from __future__ import annotations

from bento.toolkit.validators.architecture_validator import ArchitectureValidator


def _silence_report(self, report):
    # Avoid noisy prints in test output
    return None


def test_architecture_validator_empty_project(tmp_path, monkeypatch):
    """Smoke test: empty project should produce zero violations."""
    validator = ArchitectureValidator(str(tmp_path))

    # Silence report output
    monkeypatch.setattr(ArchitectureValidator, "_print_report", _silence_report, raising=False)

    # Avoid scanning the whole FS; return empty sets
    monkeypatch.setattr(validator, "_find_python_files", lambda *_: [], raising=False)
    monkeypatch.setattr(validator, "_find_application_services", lambda *_: [], raising=False)

    report = validator.validate_all()
    assert report["total_violations"] == 0
    assert report["compliance_score"] >= 0


def test_architecture_validator_detects_domain_dependency(tmp_path, monkeypatch):
    """Ensure forbidden imports in domain layer are reported."""
    domain_dir = tmp_path / "src" / "bento" / "domain"
    domain_dir.mkdir(parents=True, exist_ok=True)
    file_path = domain_dir / "sample.py"
    file_path.write_text("import sqlalchemy\n", encoding="utf-8")

    # Create application dir to satisfy scanners
    app_dir = tmp_path / "src" / "bento" / "application"
    app_dir.mkdir(parents=True, exist_ok=True)
    # Application file with bad dependency + missing uow/commit patterns
    (app_dir / "bad_service.py").write_text(
        "from bento.infrastructure.database import Session\n"
        "class BadService:\n"
        "    def handle(self):\n"
        "        repo = None\n"
        "        return repo\n",
        encoding="utf-8",
    )

    validator = ArchitectureValidator(str(tmp_path))
    monkeypatch.setattr(ArchitectureValidator, "_print_report", _silence_report, raising=False)

    report = validator.validate_all()
    assert report["total_violations"] >= 2
    assert any("sqlalchemy" in v for v in report["violations"])
