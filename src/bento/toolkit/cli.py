import argparse
import pathlib
import sys

from jinja2 import Environment, FileSystemLoader, select_autoescape


def get_jinja_env() -> Environment:
    """创建 Jinja2 环境"""
    template_dir = pathlib.Path(__file__).parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    # 添加自定义过滤器
    env.filters["snake_case"] = lambda s: s.lower()
    return env


def render(template_name, **ctx) -> str:
    """使用 Jinja2 渲染模板

    Args:
        template_name: 模板名称(str)或模板文件路径(Path)
        **ctx: 模板上下文变量
    """
    # 支持 Path 对象或字符串
    if isinstance(template_name, pathlib.Path):
        # 直接从文件渲染
        template_content = template_name.read_text(encoding="utf-8")
        from jinja2 import Template

        template = Template(template_content)
        # 使用 Jinja2 变量语法 {{ }} 和兼容旧的 ${} 语法
        result = template.render(**ctx)
        # 处理 ${var} 格式（向后兼容）
        for key, value in ctx.items():
            result = result.replace(f"${{{key}}}", str(value))
        return result
    else:
        # 从模板目录加载
        env = get_jinja_env()
        template = env.get_template(template_name)
        return template.render(**ctx)


def parse_fields(fields_str: str):
    if not fields_str:
        return []
    fields = []
    for field in fields_str.split(","):
        field = field.strip()
        if ":" in field:
            name, type_ = field.split(":", 1)
            fields.append((name.strip(), type_.strip()))
        else:
            fields.append((field, "str"))
    return fields


def generate_fields_code(fields, indent="    "):
    if not fields:
        return f"{indent}pass"
    lines = []
    for name, type_ in fields:
        lines.append(f"{indent}{name}: {type_}")
    return "\n".join(lines)


def generate_file(template_name: str, output_path: pathlib.Path, **ctx):
    try:
        code = render(template_name, **ctx)
    except Exception as e:
        print(f"⚠ Template rendering error: {e}, skipping")
        return False
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        response = input(f"{output_path} already exists. Overwrite? (y/n): ")
        if response.lower() != "y":
            print("Skipped.")
            return False
    output_path.write_text(code, encoding="utf-8")
    print(f"✓ Generated: {output_path}")
    return True


def generate_aggregate(name: str, fields, output_dir: pathlib.Path):
    fields_code = generate_fields_code(fields, indent="    ")
    return generate_file(
        "aggregate.py.tpl",
        output_dir / "domain" / f"{name.lower()}.py",
        Name=name,
        name_lower=name.lower(),
        EventName=name.lower(),  # 事件名称（小写）
        fields=fields_code,
    )


def generate_po(name: str, fields, output_dir: pathlib.Path):
    fields_lines = []
    for field_name, field_type in fields:
        if field_name == "id":
            fields_lines.append("    id: Mapped[str] = mapped_column(primary_key=True)")
        else:
            sa_type = {"int": "int", "bool": "bool", "float": "float"}.get(field_type, "str")
            fields_lines.append(f"    {field_name}: Mapped[{sa_type}]")
    fields_code = "\n".join(fields_lines)
    return generate_file(
        "po.py.tpl",
        output_dir / "infrastructure" / "models" / f"{name.lower()}_po.py",
        Name=name,
        name_lower=name.lower(),
        table_name=name.lower() + "s",
        fields=fields_code,
    )


def generate_mapper(name: str, output_dir: pathlib.Path, context: str = "shared"):
    return generate_file(
        "mapper.py.tpl",
        output_dir / "infrastructure" / "mappers" / f"{name.lower()}_mapper.py",
        Name=name,
        name_lower=name.lower(),
        context=context.lower(),
    )


def generate_repository(name: str, output_dir: pathlib.Path, context: str = "shared"):
    return generate_file(
        "repository.py.tpl",
        output_dir / "infrastructure" / "repositories" / f"{name.lower()}_repository.py",
        Name=name,
        name_lower=name.lower(),
        context=context.lower(),
    )


def generate_usecase(name: str, action: str, output_dir: pathlib.Path, context: str = "shared"):
    return generate_file(
        "usecase.py.tpl",
        output_dir / "application" / "usecases" / f"{action.lower()}_{name.lower()}.py",
        Name=name,
        Action=action,
        name_lower=name.lower(),
        action_lower=action.lower(),
        context=context.lower(),
    )


def generate_event(name: str, output_dir: pathlib.Path):
    return generate_file(
        "event.py.tpl",
        output_dir / "domain" / "events" / f"{name.lower()}_event.py",
        Name=name,
        EventName=name.lower(),
    )


def generate_aggregate_test(name: str, fields, output_dir: pathlib.Path):
    """生成聚合根单元测试"""
    return generate_file(
        "test_aggregate.py.tpl",
        output_dir / "tests" / "unit" / "domain" / f"test_{name.lower()}.py",
        Name=name,
        name_lower=name.lower(),
        fields=fields,
    )


def generate_usecase_test(name: str, action: str, output_dir: pathlib.Path):
    """生成用例单元测试"""
    return generate_file(
        "test_usecase.py.tpl",
        output_dir / "tests" / "unit" / "application" / f"test_{action.lower()}_{name.lower()}.py",
        Name=name,
        Action=action,
        name_lower=name.lower(),
        action_lower=action.lower(),
    )


def generate_repository_test(name: str, output_dir: pathlib.Path):
    """生成仓储集成测试"""
    return generate_file(
        "test_repository.py.tpl",
        output_dir / "tests" / "integration" / f"test_{name.lower()}_repository.py",
        Name=name,
        name_lower=name.lower(),
    )


def generate_project_scaffold(project_name: str, output_dir: pathlib.Path, description: str = ""):
    """生成完整的项目脚手架（Modular Monolith 架构）"""
    print(f"\n🎉 Initializing Bento project: {project_name}")
    print("📐 Architecture: Modular Monolith\n")

    project_dir = output_dir / project_name
    if project_dir.exists():
        response = input(f"{project_dir} already exists. Continue? (y/n): ")
        if response.lower() != "y":
            print("Aborted.")
            return False

    # 项目元数据
    ctx = {
        "project_name": project_name,
        "project_slug": project_name.lower().replace("-", "_").replace(" ", "_"),
        "description": description or f"{project_name} - A Bento Framework Application",
        "architecture": "modular-monolith",
    }

    # 生成配置文件
    print("📝 Generating configuration files...\n")
    generate_file("project/pyproject.toml.tpl", project_dir / "pyproject.toml", **ctx)
    generate_file("project/env.example.tpl", project_dir / ".env.example", **ctx)
    generate_file("project/.gitignore.tpl", project_dir / ".gitignore", **ctx)
    generate_file("project/pytest.ini.tpl", project_dir / "pytest.ini", **ctx)
    generate_file("project/README.md.tpl", project_dir / "README.md", **ctx)
    generate_file("project/alembic.ini.tpl", project_dir / "alembic.ini", **ctx)
    generate_file("project/Makefile.tpl", project_dir / "Makefile", **ctx)

    # 生成 VS Code 配置
    print("\n🔧 Generating VS Code configuration...\n")
    generate_file(
        "project/vscode/extensions.json.tpl", project_dir / ".vscode" / "extensions.json", **ctx
    )
    generate_file(
        "project/vscode/settings.json.tpl", project_dir / ".vscode" / "settings.json", **ctx
    )
    generate_file("project/vscode/launch.json.tpl", project_dir / ".vscode" / "launch.json", **ctx)
    generate_file("project/vscode/tasks.json.tpl", project_dir / ".vscode" / "tasks.json", **ctx)

    # 生成应用代码
    print("\n🏗️  Generating application structure...\n")
    generate_file("project/main.py.tpl", project_dir / "main.py", **ctx)
    generate_file("project/config.py.tpl", project_dir / "config.py", **ctx)

    # 生成 API 层
    generate_file("project/api/__init__.py.tpl", project_dir / "api" / "__init__.py", **ctx)
    generate_file("project/api/deps.py.tpl", project_dir / "api" / "deps.py", **ctx)
    generate_file("project/api/router.py.tpl", project_dir / "api" / "router.py", **ctx)

    # 生成测试配置
    generate_file("project/tests/conftest.py.tpl", project_dir / "tests" / "conftest.py", **ctx)

    # 创建目录结构（Modular Monolith 架构 - 按边界上下文组织）
    print("\n📁 Creating directory structure...\n")

    dirs = [
        "contexts/shared/domain",
        "contexts/shared/events",
        "tests/unit",
        "tests/integration",
        "alembic/versions",
    ]
    for d in dirs:
        (project_dir / d).mkdir(parents=True, exist_ok=True)
        (project_dir / d / "__init__.py").touch()

    # 创建 shared 上下文的说明文件
    (project_dir / "contexts" / "__init__.py").write_text(
        '"""Bounded Contexts - 边界上下文\n\n'
        "每个子目录代表一个边界上下文（Bounded Context）。\n"
        "使用 `bento gen module <Name> --context <context-name>` 生成模块。\n"
        '"""\n'
    )
    (project_dir / "contexts" / "shared" / "README.md").write_text(
        "# Shared Context\n\n"
        "共享内核 - 包含多个上下文共享的领域概念。\n\n"
        "- `domain/` - 共享的值对象和接口\n"
        "- `events/` - 集成事件（跨上下文通信）\n"
    )

    print(f"\n✅ Project '{project_name}' initialized successfully!")
    print(f"\n📍 Location: {project_dir}")
    print("📐 Architecture: Modular Monolith")
    print("\n🚀 Next steps:")
    print(f"   cd {project_name}")
    print("   cp .env.example .env")
    print("   uv pip install -e .")
    print("\n💡 Generate your first context:")
    print("   bento gen module Product --context catalog --fields 'name:str,price:float'")
    print("   uvicorn main:app --reload")
    print("\n")
    return True


def generate_module(name: str, fields, output_dir: pathlib.Path, context: str):
    """生成 DDD 模块（Modular Monolith 架构）

    Args:
        name: 模块名称（如 Product）
        fields: 字段列表
        output_dir: 输出目录
        context: 边界上下文名称（必填）
    """
    print(f"\n🚀 Generating module: {name} in context: {context}\n")
    # Modular Monolith: contexts/<context-name>/
    base_dir = output_dir / "contexts" / context.lower()

    # 创建上下文目录结构及 __init__.py 文件
    print("📁 Creating context directory structure...\n")
    context_dirs = [
        base_dir,
        base_dir / "domain",
        base_dir / "domain" / "events",
        base_dir / "application",
        base_dir / "application" / "usecases",
        base_dir / "infrastructure",
        base_dir / "infrastructure" / "models",
        base_dir / "infrastructure" / "mappers",
        base_dir / "infrastructure" / "repositories",
    ]
    for d in context_dirs:
        d.mkdir(parents=True, exist_ok=True)
        init_file = d / "__init__.py"
        if not init_file.exists():
            # 为每个目录创建带有文档字符串的 __init__.py
            layer_name = (
                d.name.capitalize() if d != base_dir else f"{context.capitalize()} 限界上下文"
            )
            init_file.write_text(f'"""{layer_name}"""\n', encoding="utf-8")
            print(f"✓ Created: {init_file}")

    field_names = [f[0] for f in fields]
    if "id" not in field_names:
        fields.insert(0, ("id", "str"))

    # 生成领域层代码
    print("\n📦 Generating domain layer...\n")
    generate_aggregate(name, fields, base_dir)
    generate_event(name + "Created", base_dir)

    # 生成基础设施层代码
    print("\n🏗️  Generating infrastructure layer...\n")
    generate_po(name, fields, base_dir)
    generate_mapper(name, base_dir, context)
    generate_repository(name, base_dir, context)

    # 生成应用层代码
    print("\n⚙️  Generating application layer...\n")
    generate_usecase(name, "Create", base_dir, context)

    # 生成测试代码（TDD）- 按上下文组织
    print("\n📝 Generating tests...\n")

    # 上下文测试放在 tests/<context>/
    ctx_test_base = output_dir / "tests" / context.lower()
    (ctx_test_base / "unit" / "domain").mkdir(parents=True, exist_ok=True)
    (ctx_test_base / "unit" / "application").mkdir(parents=True, exist_ok=True)
    (ctx_test_base / "integration").mkdir(parents=True, exist_ok=True)

    # 创建 __init__.py
    (ctx_test_base / "__init__.py").touch()
    (ctx_test_base / "unit" / "__init__.py").touch()
    (ctx_test_base / "unit" / "domain" / "__init__.py").touch()
    (ctx_test_base / "unit" / "application" / "__init__.py").touch()
    (ctx_test_base / "integration" / "__init__.py").touch()

    # 生成测试文件
    generate_file(
        "test_aggregate.py.tpl",
        ctx_test_base / "unit" / "domain" / f"test_{name.lower()}.py",
        Name=name,
        name_lower=name.lower(),
        context=context.lower(),
        fields=fields,
    )
    generate_file(
        "test_usecase.py.tpl",
        ctx_test_base / "unit" / "application" / f"test_create_{name.lower()}.py",
        Name=name,
        Action="Create",
        name_lower=name.lower(),
        action_lower="create",
        context=context.lower(),
    )
    generate_file(
        "test_repository.py.tpl",
        ctx_test_base / "integration" / f"test_{name.lower()}_repository.py",
        Name=name,
        name_lower=name.lower(),
        context=context.lower(),
    )

    print(f"\n✅ Module '{name}' generated in context '{context}' successfully!\n")


def main():
    """CLI 入口点函数"""

    # 主帮助文本
    epilog = """
Examples:
  # Initialize a new project
  bento init my-shop --description "E-commerce application"

  # Generate a complete module (aggregate + repository + use cases + tests)
  bento gen module Product --context catalog --fields "name:str,price:float,stock:int"

  # Generate individual components
  bento gen event OrderCreated --output ./my-project
  bento gen aggregate Order --fields "id:str,status:str" --output ./my-project

  # Generate in specific context
  bento gen module User --context identity --fields "email:str,name:str"

Architecture:
  Bento follows Domain-Driven Design (DDD) and Modular Monolith architecture.
  Projects are organized by bounded contexts, each containing:
    - domain/      Domain layer (aggregates, entities, events)
    - application/ Application layer (use cases, DTOs)
    - infrastructure/ Infrastructure layer (repositories, mappers)

Documentation:
  https://github.com/idpxyz/bento

Version: 0.1.0
"""

    parser = argparse.ArgumentParser(
        prog="bento",
        description="🍱 Bento Framework - Domain-Driven Design Code Generator\n\n"
        "Generate production-ready DDD projects with Modular Monolith architecture.",
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")

    sub = parser.add_subparsers(
        dest="cmd", required=True, title="commands", description="Available commands"
    )

    # init 命令 - 初始化新项目（Modular Monolith 架构）
    init_help = """
Initialize a new Bento project with complete project structure.

This creates:
  - Modular Monolith architecture with bounded contexts
  - VS Code configuration (extensions, settings, tasks, debug)
  - Makefile with common tasks (test, fmt, lint, dev)
  - Database migrations (Alembic)
  - FastAPI application setup
  - Testing configuration (Pytest)

Example:
  bento init my-shop --description "E-commerce platform"
  cd my-shop
  make dev
"""

    init = sub.add_parser(
        "init",
        help="Initialize a new Bento project",
        description=init_help,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    init.add_argument("project_name", help="Name of the project (e.g., my-shop, order-service)")
    init.add_argument("--description", default="", help="Project description (optional)")
    init.add_argument(
        "--output",
        default=".",
        type=pathlib.Path,
        help="Output directory (default: current directory)",
    )

    # gen 命令 - 生成代码骨架
    gen_help = """
Generate DDD code components.

Component types:
  module      - Complete DDD module (aggregate + repository + use cases + tests)
  aggregate   - Domain aggregate root with events
  event       - Domain event
  repository  - Repository interface and implementation
  mapper      - Data mapper (domain <-> persistence)
  usecase     - Application use case
  po          - Persistence object (SQLAlchemy model)

Examples:
  # Generate complete module
  bento gen module Product --context catalog --fields "name:str,price:float"

  # Generate standalone components
  bento gen event OrderCreated --output ./my-project
  bento gen aggregate Order --fields "customer_id:str,total:float"
"""

    g = sub.add_parser(
        "gen",
        help="Generate code components",
        description=gen_help,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    g.add_argument(
        "what",
        choices=["module", "aggregate", "usecase", "event", "repository", "mapper", "po"],
        help="Type of component to generate",
        metavar="COMPONENT",
    )
    g.add_argument("name", help="Name of the component (e.g., Product, Order, User)")
    g.add_argument("--context", default="shared", help="Bounded context name (default: shared)")
    g.add_argument(
        "--fields",
        default="",
        help='Comma-separated fields with types (e.g., "name:str,price:float,stock:int")',
    )
    g.add_argument(
        "--output",
        default=".",
        type=pathlib.Path,
        help="Output directory (default: current directory)",
    )

    args = parser.parse_args()

    try:
        if args.cmd == "init":
            # 初始化项目（Modular Monolith 架构）
            output_dir = args.output.absolute()
            generate_project_scaffold(args.project_name, output_dir, args.description)
            return 0

        # gen 命令处理
        name = args.name[0].upper() + args.name[1:]
        output_dir = args.output.absolute()
        fields = parse_fields(args.fields)
        context = args.context

        if args.what == "module":
            generate_module(name, fields, output_dir, context)
        elif args.what == "aggregate":
            generate_aggregate(name, fields, output_dir)
        elif args.what == "po":
            generate_po(name, fields, output_dir)
        elif args.what == "mapper":
            generate_mapper(name, output_dir, context)
        elif args.what == "repository":
            generate_repository(name, output_dir, context)
        elif args.what == "usecase":
            if name.startswith(("Create", "Update", "Delete", "Get", "List")):
                for action in ["Create", "Update", "Delete", "Get", "List"]:
                    if name.startswith(action):
                        entity_name = name[len(action) :]
                        generate_usecase(entity_name, action, output_dir, context)
                        break
        elif args.what == "event":
            generate_event(name, output_dir)

        return 0
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
