import sys

import pytest

import bento.toolkit.cli as cli


@pytest.mark.asyncio
async def test_cli_gen_command_and_event(tmp_path, monkeypatch):
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

    # command - CQRS 架构使用 command 替代 usecase
    # 测试 CreateBar command
    monkeypatch.setattr(sys, "argv", ["bento", "gen", "command", "CreateBar"])
    cli.main()
    out_command = tmp_path / "application" / "commands" / "create_bar.py"
    assert out_command.exists(), (
        f"Expected command file not found. Files: {list(tmp_path.rglob('*'))}"
    )
    content_command = out_command.read_text(encoding="utf-8")
    assert "Name=Bar" in content_command

    # event - 现在生成到 domain/events/ 目录
    monkeypatch.setattr(sys, "argv", ["bento", "gen", "event", "Baz"])
    cli.main()
    out_event = tmp_path / "domain" / "events" / "baz_event.py"
    assert out_event.exists(), f"Expected event file not found. Files: {list(tmp_path.rglob('*'))}"
    assert "EventName=baz" in out_event.read_text(encoding="utf-8")
