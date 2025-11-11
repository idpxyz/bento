import argparse
import pathlib
from string import Template


def render(src: pathlib.Path, **ctx) -> str:
    txt = src.read_text(encoding="utf-8")
    # allow both ${var} and {{var}} syntax (simple replacement)
    for k, v in ctx.items():
        txt = txt.replace("{{"+k+"}}", str(v))
    return Template(txt).substitute(**ctx)

def main():
    parser = argparse.ArgumentParser(prog="omnia-ddd")
    sub = parser.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("gen", help="Generate code skeletons")
    g.add_argument("what", choices=["aggregate", "usecase", "event"])
    g.add_argument("name")

    args = parser.parse_args()
    name = args.name[0].upper() + args.name[1:]
    templates = {
        "aggregate": ("src/ddd_toolkit/templates/aggregate.py.tpl", f"{args.name.lower()}_aggregate.py"),
        "usecase":   ("src/ddd_toolkit/templates/usecase.py.tpl",   f"{args.name.lower()}_usecase.py"),
        "event":     ("src/ddd_toolkit/templates/event.py.tpl",     f"{args.name.lower()}_event.py"),
    }
    tpl_path, out_name = templates[args.what]
    out = pathlib.Path(out_name)
    out.write_text(render(pathlib.Path(tpl_path), Name=name, EventName=args.name.lower()), encoding="utf-8")
    print(f"Generated: {out}")
if __name__ == "__main__":
    main()
