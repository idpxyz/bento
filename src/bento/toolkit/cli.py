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


def generate_command(name: str, action: str, output_dir: pathlib.Path, context: str = "shared"):
    """生成 Command Handler（CQRS 写操作）"""
    return generate_file(
        "command.py.tpl",
        output_dir / "application" / "commands" / f"{action.lower()}_{name.lower()}.py",
        Name=name,
        Action=action,
        name_lower=name.lower(),
        action_lower=action.lower(),
        context=context.lower(),
    )


def generate_query(name: str, action: str, output_dir: pathlib.Path, context: str = "shared"):
    """生成 Query Handler（CQRS 读操作）"""
    return generate_file(
        "query.py.tpl",
        output_dir / "application" / "queries" / f"{action.lower()}_{name.lower()}.py",
        Name=name,
        Action=action,
        name_lower=name.lower(),
        action_lower=action.lower(),
        context=context.lower(),
    )




def generate_event(name: str, output_dir: pathlib.Path, context: str = "shared"):
    """生成领域事件

    Args:
        name: 事件名称（如 ProductCreated）
        output_dir: 输出目录
        context: 上下文名称（用于生成 topic）
    """
    # 提取实体名称（去除事件后缀）
    entity_name = name
    event_name = name.lower()

    # 尝试提取实体名称（例如：ProductCreated -> Product）
    for suffix in ["Created", "Updated", "Deleted", "Changed"]:
        if name.endswith(suffix):
            entity_name = name[:-len(suffix)]
            break

    return generate_file(
        "event.py.tpl",
        output_dir / "domain" / "events" / f"{event_name}_event.py",
        Name=name,
        EventName=event_name,
        name_lower=entity_name.lower(),
        context=context.lower(),
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


def generate_bounded_context(context_name: str, output_dir: pathlib.Path, description: str = ""):
    """生成 Bounded Context 初始结构

    Args:
        context_name: Context 名称（如 catalog, order）
        output_dir: 输出目录
        description: Context 业务说明
    """
    print(f"\n🎯 Creating Bounded Context: {context_name}")
    print(f"📁 Location: {output_dir / 'contexts' / context_name.lower()}\n")

    context_dir = output_dir / "contexts" / context_name.lower()

    if context_dir.exists():
        response = input(f"{context_dir} already exists. Continue? (y/n): ")
        if response.lower() != "y":
            print("Aborted.")
            return False

    # 创建标准目录结构
    print("📁 Creating directory structure...\n")

    directories = [
        # Domain Layer
        context_dir / "domain" / "model",
        context_dir / "domain" / "events",
        context_dir / "domain" / "services",
        context_dir / "domain" / "ports",
        # Application Layer (CQRS Style)
        context_dir / "application" / "commands",
        context_dir / "application" / "queries",
        context_dir / "application" / "dto" / "requests",
        context_dir / "application" / "dto" / "responses",
        context_dir / "application" / "services",
        context_dir / "application" / "mappers",
        # Infrastructure Layer
        context_dir / "infrastructure" / "persistence" / "models",
        context_dir / "infrastructure" / "persistence" / "mappers",
        context_dir / "infrastructure" / "persistence" / "repositories",
        context_dir / "infrastructure" / "messaging",
        context_dir / "infrastructure" / "external",
        # Interfaces Layer
        context_dir / "interfaces" / "api",
        context_dir / "interfaces" / "cli",
        context_dir / "interfaces" / "events",
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        init_file = directory / "__init__.py"

        # 生成带文档字符串的 __init__.py
        layer_name = _get_layer_doc(directory, context_name)
        init_file.write_text(f'"""{layer_name}"""\n', encoding="utf-8")
        print(f"✓ Created: {directory.relative_to(output_dir)}")

    # 创建 README.md
    readme_content = f"""# {context_name.capitalize()} Context

## 业务说明

{description or f"{context_name.capitalize()} 限界上下文"}

## 目录结构

```
{context_name.lower()}/
├── domain/              # 领域层（核心业务逻辑）
│   ├── model/          # 聚合根、实体、值对象
│   ├── events/         # 领域事件
│   ├── services/       # 领域服务
│   └── ports/          # 端口（Repository 接口等）
│
├── application/         # 应用层（CQRS风格）
│   ├── commands/       # Command handlers (写操作)
│   ├── queries/        # Query handlers (读操作)
│   ├── dto/            # 数据传输对象
│   │   ├── requests/   # Request DTOs
│   │   └── responses/  # Response DTOs
│   ├── services/       # Application services (复杂编排)
│   └── mappers/        # DTO <-> Domain 映射
│
├── infrastructure/      # 基础设施层（技术实现）
│   ├── persistence/    # 持久化（ORM、Repository 实现）
│   ├── messaging/      # 消息传递
│   └── external/       # 外部服务适配器
│
└── interfaces/          # 接口层（驱动适配器）
    ├── api/            # REST API
    ├── cli/            # CLI 命令
    └── events/         # 事件订阅
```

## 使用指南

### 生成模块

```bash
# 在此 Context 中生成完整模块
bento gen module <Name> --context {context_name.lower()} --fields "field1:type1,field2:type2"
```

### 依赖规则

- ✅ Domain 层：无外部依赖
- ✅ Application 层：只依赖 Domain
- ✅ Infrastructure 层：实现 Domain 的 Ports
- ✅ Interfaces 层：只依赖 Application

### 测试

```bash
# 运行此 Context 的测试
pytest tests/{context_name.lower()}/
```

## 架构验证

```bash
# 验证此 Context 的架构合规性
bento validate --context {context_name.lower()}
```

---

**创建时间**: {_get_timestamp()}
**架构**: Modular Monolith
**参考文档**: `/docs/architecture/BOUNDED_CONTEXT_STRUCTURE.md`
"""

    (context_dir / "README.md").write_text(readme_content, encoding="utf-8")
    print(f"\n✓ Created: {(context_dir / 'README.md').relative_to(output_dir)}")

    # 创建 domain/exceptions.py
    exceptions_content = f'''"""Domain Exceptions for {context_name.capitalize()} Context"""

from bento.domain.aggregate import DomainException


class {context_name.capitalize()}Exception(DomainException):
    """Base exception for {context_name.capitalize()} context"""
    pass


# 添加更多特定异常...
# class InvalidProductError({context_name.capitalize()}Exception):
#     """产品验证失败"""
#     pass
'''

    (context_dir / "domain" / "exceptions.py").write_text(exceptions_content, encoding="utf-8")
    print("✓ Created: domain/exceptions.py")

    # 创建测试目录结构
    test_dir = output_dir / "tests" / context_name.lower()
    test_directories = [
        test_dir / "unit" / "domain",
        test_dir / "unit" / "application",
        test_dir / "integration",
    ]

    print("\n📝 Creating test structure...\n")
    for directory in test_directories:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "__init__.py").touch()
        print(f"✓ Created: {directory.relative_to(output_dir)}")

    print(f"\n✅ Bounded Context '{context_name}' created successfully!")
    print(f"\n📍 Location: {context_dir.relative_to(output_dir)}")
    print("\n🚀 Next steps:")
    print("   # Generate your first module in this context")
    print(
        f"   bento gen module <Name> --context {context_name.lower()}"
        "--fields 'field1:type1,field2:type2'"
    )
    print("\n   # Example:")
    print(
        f"   bento gen module Product --context {context_name.lower()} \
        --fields 'name:str,sku:str,price:float'"
    )
    print()

    return True


def _get_layer_doc(directory: pathlib.Path, context_name: str) -> str:
    """生成分层文档字符串"""
    layer_map = {
        "domain": f"{context_name.capitalize()} - Domain Layer",
        "model": "Domain Models (Aggregates, Entities, Value Objects)",
        "services": "Domain Services or Application Services",
        "ports": "Domain Ports (Interfaces)",
        "application": f"{context_name.capitalize()} - Application Layer (CQRS)",
        "commands": "Command Handlers (Write Operations)",
        "queries": "Query Handlers (Read Operations)",
        "dto": "Data Transfer Objects",
        "requests": "Request DTOs",
        "responses": "Response DTOs",
        "mappers": "Mappers (DTO <-> Domain)",
        "infrastructure": f"{context_name.capitalize()} - Infrastructure Layer",
        "persistence": "Persistence Layer",
        "models": "Persistence Objects (ORM Models)",
        "repositories": "Repository Implementations",
        "messaging": "Messaging & Event Handlers",
        "external": "External Service Adapters",
        "interfaces": f"{context_name.capitalize()} - Interfaces Layer",
        "api": "REST API Endpoints",
        "cli": "CLI Commands",
    }

    # 特殊处理：events 可能是 domain/events 或 interfaces/events
    if directory.name == "events":
        if "domain" in str(directory):
            return "Domain Events"
        elif "interfaces" in str(directory):
            return "Event Subscribers"

    dir_name = directory.name
    return layer_map.get(dir_name, f"{context_name.capitalize()} - {dir_name.capitalize()}")


def _get_timestamp() -> str:
    """获取当前时间戳"""
    from datetime import datetime

    return datetime.now().strftime("%Y-%m-%d")


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
        base_dir / "application" / "commands",
        base_dir / "application" / "queries",
        base_dir / "application" / "dto" / "requests",
        base_dir / "application" / "dto" / "responses",
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
    generate_event(name + "Created", base_dir, context)

    # 生成基础设施层代码
    print("\n🏗️  Generating infrastructure layer...\n")
    generate_po(name, fields, base_dir)
    generate_mapper(name, base_dir, context)
    generate_repository(name, base_dir, context)

    # 生成应用层代码（CQRS 风格）
    print("\n⚙️  Generating application layer (CQRS)...\n")
    generate_command(name, "Create", base_dir, context)
    generate_command(name, "Update", base_dir, context)
    generate_command(name, "Delete", base_dir, context)
    generate_query(name, "Get", base_dir, context)
    generate_query(name, "List", base_dir, context)

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
    # Domain tests
    generate_file(
        "test_aggregate.py.tpl",
        ctx_test_base / "unit" / "domain" / f"test_{name.lower()}.py",
        Name=name,
        name_lower=name.lower(),
        context=context.lower(),
        fields=fields,
    )

    # Application tests (CQRS - Command tests)
    for action in ["Create", "Update", "Delete"]:
        generate_file(
            "test_command.py.tpl",
            ctx_test_base / "unit" / "application" / f"test_{action.lower()}_{name.lower()}.py",
            Name=name,
            Action=action,
            name_lower=name.lower(),
            action_lower=action.lower(),
            context=context.lower(),
        )

    # Application tests (CQRS - Query tests)
    for action in ["Get", "List"]:
        generate_file(
            "test_query.py.tpl",
            ctx_test_base / "unit" / "application" / f"test_{action.lower()}_{name.lower()}.py",
            Name=name,
            Action=action,
            name_lower=name.lower(),
            action_lower=action.lower(),
            context=context.lower(),
        )

    # Integration tests
    generate_file(
        "test_repository.py.tpl",
        ctx_test_base / "integration" / f"test_{name.lower()}_repository.py",
        Name=name,
        name_lower=name.lower(),
        context=context.lower(),
    )

    print(f"\n✅ Module '{name}' generated in context '{context}' successfully!\n")


def run_validation(args):
    """执行架构验证"""
    try:
        from bento.toolkit.validators import ArchitectureValidator

        print("🔍 Running Bento Framework Architecture Validation")
        print("=" * 50)

        validator = ArchitectureValidator(args.project_path)
        report = validator.validate_all()

        # 输出报告到文件
        if args.output:
            import json

            with open(args.output, "w") as f:
                json.dump(report, f, indent=2)
            print(f"\n📄 Validation report saved to: {args.output}")

        # 如果设置了失败标志且有违规，返回错误代码
        if args.fail_on_violations and report["total_violations"] > 0:
            print(f"\n❌ Validation failed with {report['total_violations']} violations")
            return 1

        if report["total_violations"] == 0:
            print("\n🎉 All validations passed! Architecture is compliant.")
            return 0
        else:
            print(f"\n⚠️ Found {report['total_violations']} violations, but continuing...")
            return 0

    except ImportError as e:
        print(f"❌ Error: Cannot import validator: {e}")
        print("💡 Make sure bento.toolkit.validators is properly installed")
        return 1
    except Exception as e:
        print(f"❌ Validation error: {e}")
        return 1


def run_contracts_command(args):
    """执行 Contract-as-Code 命令"""
    try:
        from bento.contracts import ContractLoader
        from bento.contracts.gates import ContractGate

        contracts_path = args.contracts_path

        if args.contracts_cmd == "validate":
            print("🔍 Validating Contract-as-Code definitions")
            print("=" * 50)
            print(f"📁 Contracts path: {contracts_path}")

            gate = ContractGate(
                contracts_root=contracts_path,
                require_state_machines=args.require_state_machines,
                require_reason_codes=args.require_reason_codes,
                require_routing=args.require_routing,
            )
            result = gate.check()

            # Print warnings
            for warning in result.warnings:
                print(f"⚠️  {warning}")

            # Print errors
            for error in result.errors:
                print(f"❌ {error}")

            if result.passed:
                print("\n✅ All contract validations passed!")
                return 0
            else:
                print(f"\n❌ Contract validation failed with {len(result.errors)} error(s)")
                return 1

        elif args.contracts_cmd == "list":
            print("📋 Contract-as-Code Definitions")
            print("=" * 50)
            print(f"📁 Contracts path: {contracts_path}")

            try:
                contracts = ContractLoader.load_from_dir(contracts_path)
            except Exception as e:
                print(f"❌ Failed to load contracts: {e}")
                return 1

            list_type = args.type

            if list_type in ("all", "state-machines"):
                print("\n🔄 State Machines:")
                aggregates = contracts.state_machines.aggregates
                if aggregates:
                    for agg in aggregates:
                        states = contracts.state_machines.get_states(agg)
                        print(f"  • {agg}: {len(states)} states")
                else:
                    print("  (none)")

            if list_type in ("all", "reason-codes"):
                print("\n📝 Reason Codes:")
                codes = contracts.reason_codes.all()
                if codes:
                    for code in codes[:10]:  # Show first 10
                        print(f"  • {code.code} ({code.http_status}): {code.message[:40]}...")
                    if len(codes) > 10:
                        print(f"  ... and {len(codes) - 10} more")
                else:
                    print("  (none)")

            if list_type in ("all", "routing"):
                print("\n🔀 Event Routing:")
                routes = contracts.routing.all_routes()
                if routes:
                    for route in routes[:10]:  # Show first 10
                        print(f"  • {route.event_type} → {route.topic}")
                    if len(routes) > 10:
                        print(f"  ... and {len(routes) - 10} more")
                else:
                    print("  (none)")

            print()
            return 0

    except ImportError as e:
        print(f"❌ Error: Cannot import contracts module: {e}")
        print("💡 Make sure PyYAML is installed: pip install pyyaml")
        return 1
    except Exception as e:
        print(f"❌ Contract command error: {e}")
        return 1


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
Generate DDD code components (CQRS Architecture).

Component types:
  context     - Create a complete Bounded Context structure
  module      - Complete DDD module (aggregate + repository + commands + queries + tests)
  aggregate   - Domain aggregate root with events
  event       - Domain event
  repository  - Repository interface and implementation
  mapper      - Data mapper (domain <-> persistence)
  command     - Command handler (write operations: Create/Update/Delete)
  query       - Query handler (read operations: Get/List/Search)
  po          - Persistence object (SQLAlchemy model)

Examples:
  # Create a new Bounded Context
  bento gen context catalog --description "Product catalog management"
  bento gen context order --description "Order processing workflow"

  # Generate complete module in a context (CQRS style)
  bento gen module Product --context catalog --fields "name:str,sku:str,price:float"
  # Generates: commands/ queries/ domain/ infrastructure/ tests/

  # Generate standalone components (CQRS)
  bento gen command Product Create --context catalog  # CreateProductHandler
  bento gen command Product Publish --context catalog # PublishProductHandler
  bento gen query Product Get --context catalog       # GetProductHandler
  bento gen query Product Search --context catalog    # SearchProductHandler

  # Generate domain components
  bento gen event OrderCreated --context order
  bento gen aggregate Order --fields "customer_id:str,total:float" --context order
"""

    g = sub.add_parser(
        "gen",
        help="Generate code components",
        description=gen_help,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    g.add_argument(
        "what",
        choices=[
            "context",
            "module",
            "aggregate",
            "command",
            "query",
            "event",
            "repository",
            "mapper",
            "po",
        ],
        help="Type of component to generate",
        metavar="COMPONENT",
    )
    g.add_argument("name", help="Name of the component (e.g., Product, Order, User, catalog)")
    g.add_argument("--context", default="shared", help="Bounded context name (default: shared)")
    g.add_argument(
        "--description",
        default="",
        help="Description for context or module",
    )
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

    # validate 命令 - 架构验证
    validate_help = """
Validate Bento Framework architecture compliance.

This command checks:
  - Layer dependency violations (Domain/Application/Infrastructure)
  - ApplicationService pattern compliance
  - UnitOfWork usage patterns
  - Domain layer purity

Example:
  bento validate --project-path . --output report.json
  bento validate --context catalog
"""

    validate = sub.add_parser(
        "validate",
        help="Validate architecture compliance",
        description=validate_help,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    validate.add_argument(
        "--project-path",
        default=".",
        help="Project root path to validate (default: current directory)",
    )
    validate.add_argument("--output", help="Output validation report to JSON file")
    validate.add_argument("--context", help="Validate specific bounded context only")
    validate.add_argument(
        "--fail-on-violations", action="store_true", help="Exit with error code if violations found"
    )

    # contracts 命令 - Contract-as-Code 验证
    contracts_help = """
Validate and inspect Contract-as-Code definitions.

This command checks:
  - State machine definitions (YAML)
  - Reason codes catalog (JSON)
  - Event routing matrix (YAML)
  - Event schemas (JSON Schema)

Example:
  bento contracts validate ./contracts
  bento contracts list ./contracts --type state-machines
  bento contracts list ./contracts --type reason-codes
"""

    contracts_parser = sub.add_parser(
        "contracts",
        help="Contract-as-Code validation and inspection",
        description=contracts_help,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    contracts_sub = contracts_parser.add_subparsers(
        dest="contracts_cmd", required=True, title="contract commands"
    )

    # contracts validate
    cv = contracts_sub.add_parser("validate", help="Validate contract files")
    cv.add_argument(
        "contracts_path",
        nargs="?",
        default="./contracts",
        help="Path to contracts directory (default: ./contracts)",
    )
    cv.add_argument(
        "--require-state-machines",
        action="store_true",
        help="Fail if no state machines found",
    )
    cv.add_argument(
        "--require-reason-codes",
        action="store_true",
        help="Fail if no reason codes found",
    )
    cv.add_argument(
        "--require-routing",
        action="store_true",
        help="Fail if no routing matrix found",
    )

    # contracts list
    cl = contracts_sub.add_parser("list", help="List contract definitions")
    cl.add_argument(
        "contracts_path",
        nargs="?",
        default="./contracts",
        help="Path to contracts directory (default: ./contracts)",
    )
    cl.add_argument(
        "--type",
        choices=["all", "state-machines", "reason-codes", "routing"],
        default="all",
        help="Type of contracts to list (default: all)",
    )

    args = parser.parse_args()

    try:
        if args.cmd == "init":
            # 初始化项目（Modular Monolith 架构）
            output_dir = args.output.absolute()
            generate_project_scaffold(args.project_name, output_dir, args.description)
            return 0

        elif args.cmd == "contracts":
            # Contract-as-Code 验证和检查
            return run_contracts_command(args)

        elif args.cmd == "validate":
            # 架构验证
            return run_validation(args)

        # gen 命令处理
        output_dir = args.output.absolute()

        if args.what == "context":
            # 生成 Bounded Context
            context_name = args.name.lower()
            generate_bounded_context(context_name, output_dir, args.description)
        else:
            # 其他组件生成
            name = args.name[0].upper() + args.name[1:]
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
            elif args.what == "command":
                # CQRS: Command handlers (write operations)
                # Support both formats:
                # 1. bento gen command Product Create  (entity + action)
                # 2. bento gen command CreateProduct   (combined name)
                if " " in name:
                    # Format: "Product Create"
                    parts = name.split()
                    entity_name = parts[0]
                    action = parts[1] if len(parts) > 1 else "Create"
                elif name.startswith(("Create", "Update", "Delete")):
                    # Format: "CreateProduct"
                    for action in ["Create", "Update", "Delete"]:
                        if name.startswith(action):
                            entity_name = name[len(action):]
                            break
                else:
                    # Default: treat whole name as entity, action = Create
                    entity_name = name
                    action = "Create"
                generate_command(entity_name, action, output_dir, context)

            elif args.what == "query":
                # CQRS: Query handlers (read operations)
                # Support both formats:
                # 1. bento gen query Product Get  (entity + action)
                # 2. bento gen query GetProduct   (combined name)
                if " " in name:
                    # Format: "Product Get"
                    parts = name.split()
                    entity_name = parts[0]
                    action = parts[1] if len(parts) > 1 else "Get"
                elif name.startswith(("Get", "List", "Search", "Find")):
                    # Format: "GetProduct"
                    for action in ["Get", "List", "Search", "Find"]:
                        if name.startswith(action):
                            entity_name = name[len(action):]
                            break
                else:
                    # Default: treat whole name as entity, action = Get
                    entity_name = name
                    action = "Get"
                generate_query(entity_name, action, output_dir, context)
            elif args.what == "event":
                generate_event(name, output_dir, context)

        return 0
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
