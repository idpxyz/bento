from __future__ import annotations

import builtins

from bento.toolkit import cli


def test_parse_and_generate_fields_code():
    fields = cli.parse_fields("name:str,price:float,active")
    assert ("name", "str") in fields
    assert ("price", "float") in fields
    assert ("active", "str") in fields  # default type

    code = cli.generate_fields_code(fields, indent="  ")
    assert "name: str" in code
    assert "price: float" in code
    assert "active: str" in code


def test_generate_file_with_stubbed_render(tmp_path, monkeypatch):
    # Stub render to avoid Jinja dependency and write predictable content
    monkeypatch.setattr(cli, "render", lambda *_args, **_kwargs: "CONTENT", raising=False)

    out_path = tmp_path / "out.txt"
    created = cli.generate_file("any.tpl", out_path, foo="bar")
    assert created is True
    assert out_path.read_text() == "CONTENT"

    # If file exists and user declines overwrite, should return False
    monkeypatch.setattr(builtins, "input", lambda *_args, **_kwargs: "n")
    created_again = cli.generate_file("any.tpl", out_path, foo="bar")
    assert created_again is False


def test_generate_file_overwrite_yes(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "render", lambda *_args, **_kwargs: "NEW", raising=False)
    out_path = tmp_path / "overwrite.txt"
    out_path.write_text("OLD", encoding="utf-8")
    monkeypatch.setattr(builtins, "input", lambda *_args, **_kwargs: "y")
    created = cli.generate_file("any.tpl", out_path, foo="bar")
    assert created is True
    assert out_path.read_text() == "NEW"


def test_render_from_path(tmp_path):
    template_file = tmp_path / "tmpl.txt"
    template_file.write_text("Hello {{ name }} ${name}", encoding="utf-8")
    result = cli.render(template_file, name="World")
    assert "World" in result
    # Both Jinja and ${} replacements should apply
    assert result == "Hello World World"


def test_generate_command_smoke(tmp_path, monkeypatch):
    # Avoid real rendering by stubbing render to constant text
    monkeypatch.setattr(cli, "render", lambda *_args, **_kwargs: "CMD", raising=False)
    output_dir = tmp_path / "mod"
    created = cli.generate_command("Product", "Create", output_dir, context="catalog")
    assert created is True
    generated = output_dir / "application" / "commands" / "create_product.py"
    assert generated.read_text() == "CMD"


def test_get_jinja_env_smoke(monkeypatch):
    # Stub FileSystemLoader to avoid filesystem dependency
    monkeypatch.setattr(cli, "FileSystemLoader", lambda *a, **k: None, raising=False)
    env = cli.get_jinja_env()
    # Filters should be registered
    assert "snake_case" in env.filters
    assert env.trim_blocks is True


def test_parse_fields_empty_and_single():
    assert cli.parse_fields("") == []
    single = cli.parse_fields("title")
    assert single == [("title", "str")]
