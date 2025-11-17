import sys

import pytest

import bento.toolkit.cli as cli


@pytest.mark.asyncio
async def test_cli_gen_usecase_and_event(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def fake_render(src, **ctx):
        # echo inputs so we don't need template files
        # src can be a string (template name) or Path object
        if hasattr(src, "name"):
            src_name = src.name
        else:
            src_name = src
        return f"what={src_name}, Name={ctx['Name']}, EventName={ctx.get('EventName', 'unknown')}"

    monkeypatch.setattr(cli, "render", fake_render)

    # usecase - 需要指定action前缀 (Create, Update, etc.)
    # 测试 CreateBar usecase
    monkeypatch.setattr(sys, "argv", ["omnia-ddd", "gen", "usecase", "CreateBar"])
    cli.main()
    out_usecase = tmp_path / "application" / "usecases" / "create_bar.py"
    assert out_usecase.exists(), (
        f"Expected usecase file not found. Files: {list(tmp_path.rglob('*'))}"
    )
    content_usecase = out_usecase.read_text(encoding="utf-8")
    assert "Name=Bar" in content_usecase

    # event - 现在生成到 domain/events/ 目录
    monkeypatch.setattr(sys, "argv", ["omnia-ddd", "gen", "event", "Baz"])
    cli.main()
    out_event = tmp_path / "domain" / "events" / "baz_event.py"
    assert out_event.exists(), f"Expected event file not found. Files: {list(tmp_path.rglob('*'))}"
    assert "EventName=baz" in out_event.read_text(encoding="utf-8")
