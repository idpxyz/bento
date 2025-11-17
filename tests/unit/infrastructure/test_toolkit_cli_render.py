from pathlib import Path

from bento.toolkit.cli import render


def test_render_template_substitutions(tmp_path: Path):
    tpl = tmp_path / "tpl.txt"
    tpl.write_text("Hello ${Name}, id={{id}}", encoding="utf-8")

    out = render(tpl, Name="World", id=123)
    assert out == "Hello World, id=123"
