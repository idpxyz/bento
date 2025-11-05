import importlib.util
import inspect
import json
import sys
from pathlib import Path
from typing import List, Tuple

import typer
from rich import print

BASE_DIR = Path(__file__).resolve().parents[1]
ERROR_CODE_DIR = BASE_DIR / "src" / "idp" / "framework" / "exception" / "error_codes"
sys.path.append(str(BASE_DIR))

from idp.framework.exception.metadata import ErrorCode  # 保证你使用的是新的 metadata.py

app = typer.Typer(help="统一错误码文档生成工具")

def find_error_codes_in_module(module_path: Path) -> List[Tuple[str, ErrorCode]]:
    error_codes = []
    spec = importlib.util.spec_from_file_location(module_path.stem, str(module_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    for name, obj in inspect.getmembers(module):
        if isinstance(obj, ErrorCode):
            error_codes.append((name, obj))
    return error_codes

def generate_markdown_table(error_code_list: List[Tuple[str, ErrorCode]]) -> str:
    lines = ["| 变量名 | 错误码 | 消息 | HTTP状态码 |",
             "|--------|--------|------|-------------|"]
    for var_name, code in error_code_list:
        lines.append(f"| {var_name} | {code.code} | {code.message} | {code.http_status} |")
    return "\n".join(lines)

def generate_json(error_code_list: List[Tuple[str, ErrorCode]]) -> str:
    return json.dumps([
        {
            "name": var_name,
            "code": code.code,
            "message": code.message,
            "http_status": code.http_status
        } for var_name, code in error_code_list
    ], indent=2, ensure_ascii=False)

@app.command()
def generate(
    format: str = typer.Option("markdown", "--format", "-f", help="输出格式：markdown 或 json"),
    output: str = typer.Option("ERROR_CODES.md", "--output", "-o", help="输出文件路径")
):
    """生成错误码文档"""
    all_codes = []
    for py_file in ERROR_CODE_DIR.glob("*.py"):
        codes = find_error_codes_in_module(py_file)
        all_codes.extend(codes)

    if format == "markdown":
        content = "# 🚨 项目错误码文档\n\n" + generate_markdown_table(all_codes)
    elif format == "json":
        content = generate_json(all_codes)
    else:
        print("[red]❌ 不支持的格式: 必须是 markdown 或 json[/red]")
        raise typer.Exit(code=1)

    output_path = Path(output)
    output_path.write_text(content, encoding="utf-8")
    print(f"[green]✅ 已生成: {output_path}[/green]")

if __name__ == "__main__":
    app()
