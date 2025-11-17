import sys

import pytest

import bento.toolkit.cli as cli


@pytest.mark.asyncio
async def test_cli_gen_aggregate_writes_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def fake_render(src, **ctx):
        # Handle both string template names and Path objects
        return f"Name={ctx['Name']}, EventName={ctx.get('EventName', 'unknown')}"

    monkeypatch.setattr(cli, "render", fake_render)

    monkeypatch.setenv("PYTHONIOENCODING", "utf-8")
    monkeypatch.setenv("LC_ALL", "C.UTF-8")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "omnia-ddd",
            "gen",
            "aggregate",
            "Foo",
        ],
    )

    cli.main()

    # 文件现在生成到 domain/foo.py（模块化单体架构）
    out = tmp_path / "domain" / "foo.py"
    assert out.exists(), f"Expected file not found. Files in tmp_path: {list(tmp_path.rglob('*'))}"
    content = out.read_text(encoding="utf-8")
    assert "Name=Foo" in content and "EventName=foo" in content
