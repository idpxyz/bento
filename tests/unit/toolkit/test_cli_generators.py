"""Tests for CLI code generation functions."""

from __future__ import annotations

from bento.toolkit import cli


def test_generate_aggregate_creates_file(tmp_path, monkeypatch):
    """Test aggregate generation."""
    monkeypatch.setattr(cli, "render", lambda *_args, **_kwargs: "AGGREGATE_CODE")
    output_dir = tmp_path / "project"

    created = cli.generate_aggregate("Product", [("name", "str"), ("price", "float")], output_dir)

    assert created is True
    generated = output_dir / "domain" / "product.py"
    assert generated.read_text() == "AGGREGATE_CODE"


def test_generate_po_creates_file(tmp_path, monkeypatch):
    """Test PO (Persistent Object) generation."""
    monkeypatch.setattr(cli, "render", lambda *_args, **_kwargs: "PO_CODE")
    output_dir = tmp_path / "project"

    created = cli.generate_po("Product", [("id", "str"), ("name", "str")], output_dir)

    assert created is True
    generated = output_dir / "infrastructure" / "models" / "product_po.py"
    assert generated.read_text() == "PO_CODE"


def test_generate_mapper_creates_file(tmp_path, monkeypatch):
    """Test mapper generation."""
    monkeypatch.setattr(cli, "render", lambda *_args, **_kwargs: "MAPPER_CODE")
    output_dir = tmp_path / "project"

    created = cli.generate_mapper("Product", output_dir, context="catalog")

    assert created is True
    generated = output_dir / "infrastructure" / "mappers" / "product_mapper.py"
    assert generated.read_text() == "MAPPER_CODE"


def test_generate_repository_creates_file(tmp_path, monkeypatch):
    """Test repository generation."""
    monkeypatch.setattr(cli, "render", lambda *_args, **_kwargs: "REPO_CODE")
    output_dir = tmp_path / "project"

    created = cli.generate_repository("Product", output_dir, context="catalog")

    assert created is True
    generated = output_dir / "infrastructure" / "repositories" / "product_repository.py"
    assert generated.read_text() == "REPO_CODE"


def test_generate_command_creates_file(tmp_path, monkeypatch):
    """Test command generation."""
    monkeypatch.setattr(cli, "render", lambda *_args, **_kwargs: "COMMAND_CODE")
    output_dir = tmp_path / "project"

    created = cli.generate_command("Product", "Create", output_dir, context="catalog")

    assert created is True
    generated = output_dir / "application" / "commands" / "create_product.py"
    assert generated.read_text() == "COMMAND_CODE"


def test_generate_query_creates_file(tmp_path, monkeypatch):
    """Test query generation."""
    monkeypatch.setattr(cli, "render", lambda *_args, **_kwargs: "QUERY_CODE")
    output_dir = tmp_path / "project"

    created = cli.generate_query("Product", "Get", output_dir, context="catalog")

    assert created is True
    generated = output_dir / "application" / "queries" / "get_product.py"
    assert generated.read_text() == "QUERY_CODE"


def test_generate_event_calls_generate_file(tmp_path, monkeypatch):
    """Test event generation calls generate_file."""
    generate_file_called = {"count": 0}

    def mock_generate_file(*args, **kwargs):
        generate_file_called["count"] += 1
        return True

    monkeypatch.setattr(cli, "generate_file", mock_generate_file)
    output_dir = tmp_path / "project"

    created = cli.generate_event("ProductCreated", output_dir, context="catalog")

    assert created is True
    assert generate_file_called["count"] == 1


def test_generate_aggregate_test_creates_file(tmp_path, monkeypatch):
    """Test aggregate test generation."""
    monkeypatch.setattr(cli, "render", lambda *_args, **_kwargs: "TEST_CODE")
    output_dir = tmp_path / "project"

    created = cli.generate_aggregate_test("Product", [("name", "str")], output_dir)

    assert created is True
    generated = output_dir / "tests" / "unit" / "domain" / "test_product.py"
    assert generated.read_text() == "TEST_CODE"


def test_generate_repository_test_creates_file(tmp_path, monkeypatch):
    """Test repository test generation."""
    monkeypatch.setattr(cli, "render", lambda *_args, **_kwargs: "TEST_CODE")
    output_dir = tmp_path / "project"

    created = cli.generate_repository_test("Product", output_dir)

    assert created is True
    generated = output_dir / "tests" / "integration" / "test_product_repository.py"
    assert generated.read_text() == "TEST_CODE"


def test_generate_bounded_context_creates_structure(tmp_path, monkeypatch):
    """Test bounded context generation."""
    monkeypatch.setattr(
        "builtins.input",
        lambda *_args, **_kwargs: "y",
    )
    output_dir = tmp_path / "project"

    created = cli.generate_bounded_context("catalog", output_dir, description="Catalog context")

    assert created is True
    context_dir = output_dir / "contexts" / "catalog"
    assert (context_dir / "domain" / "model").exists()
    assert (context_dir / "application" / "commands").exists()
    assert (context_dir / "infrastructure" / "persistence" / "models").exists()
    assert (context_dir / "interfaces" / "api").exists()
    assert (context_dir / "README.md").exists()


def test_generate_bounded_context_abort_on_exists(tmp_path, monkeypatch):
    """Test bounded context generation aborts if context exists."""
    context_dir = tmp_path / "project" / "contexts" / "catalog"
    context_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        "builtins.input",
        lambda *_args, **_kwargs: "n",
    )
    output_dir = tmp_path / "project"

    created = cli.generate_bounded_context("catalog", output_dir)

    assert created is False
