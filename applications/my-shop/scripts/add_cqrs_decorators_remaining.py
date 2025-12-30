#!/usr/bin/env python3
"""批量添加 CQRS 装饰器到剩余的 Handlers (Order + User)"""

import re
from pathlib import Path

# Order & User Handler 文件列表
ORDER_COMMANDS = [
    "contexts/ordering/application/commands/create_order.py",
    "contexts/ordering/application/commands/cancel_order.py",
    "contexts/ordering/application/commands/pay_order.py",
    "contexts/ordering/application/commands/ship_order.py",
]

ORDER_QUERIES = [
    "contexts/ordering/application/queries/get_order.py",
    "contexts/ordering/application/queries/list_orders.py",
]

USER_COMMANDS = [
    "contexts/identity/application/commands/create_user.py",
]

USER_QUERIES = [
    "contexts/identity/application/queries/get_user.py",
]


def add_decorator_to_file(file_path: Path, is_command: bool):
    """为文件添加装饰器"""
    if not file_path.exists():
        print(f"⚠️  文件不存在: {file_path}")
        return False

    content = file_path.read_text()

    # 检查是否已经有装饰器
    if "@command_handler" in content or "@query_handler" in content:
        print(f"✅ {file_path.name} 已有装饰器，跳过")
        return False

    # 确定装饰器类型
    decorator = "command_handler" if is_command else "query_handler"
    handler_type = "Command" if is_command else "Query"

    # 更新导入
    if f"from bento.application.cqrs import {handler_type}Handler" in content:
        content = content.replace(
            f"from bento.application.cqrs import {handler_type}Handler",
            f"from bento.application import {handler_type}Handler, {decorator}",
        )
    elif "from bento.application import" in content:
        # 已经有 from bento.application import，添加装饰器
        content = re.sub(
            r"from bento\.application import (.*)",
            lambda m: f"from bento.application import {m.group(1)}, {decorator}"
            if decorator not in m.group(1)
            else m.group(0),
            content,
        )
    else:
        # 没有相关导入，需要添加
        import_line = f"from bento.application import {handler_type}Handler, {decorator}\n"
        # 在 dataclass 导入之后添加
        if "from dataclasses import dataclass" in content:
            content = content.replace(
                "from dataclasses import dataclass\n",
                f"from dataclasses import dataclass\n\n{import_line}",
            )
        else:
            # 如果没有 dataclass，在第一个导入后添加
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if line.startswith("from ") or line.startswith("import "):
                    continue
                else:
                    lines.insert(i, import_line)
                    break
            content = "\n".join(lines)

    # 查找 Handler 类定义并添加装饰器
    handler_pattern = rf"^class \w+Handler\({handler_type}Handler\["

    if re.search(handler_pattern, content, re.MULTILINE):
        # 在类定义前添加装饰器
        content = re.sub(
            handler_pattern, f"@{decorator}\n\\g<0>", content, count=1, flags=re.MULTILINE
        )

        file_path.write_text(content)
        print(f"✨ {file_path.name} 添加装饰器成功")
        return True
    else:
        print(f"⚠️  {file_path.name} 未找到 Handler 类")
        return False


def main():
    """主函数"""
    base_dir = Path("/workspace/bento/applications/my-shop")

    print("🚀 开始批量添加 CQRS 装饰器（Order + User）...\n")

    # 处理 Order Commands
    print("📝 处理 Order Commands:")
    for file_rel_path in ORDER_COMMANDS:
        file_path = base_dir / file_rel_path
        add_decorator_to_file(file_path, is_command=True)

    # 处理 Order Queries
    print("\n📖 处理 Order Queries:")
    for file_rel_path in ORDER_QUERIES:
        file_path = base_dir / file_rel_path
        add_decorator_to_file(file_path, is_command=False)

    # 处理 User Commands
    print("\n👤 处理 User Commands:")
    for file_rel_path in USER_COMMANDS:
        file_path = base_dir / file_rel_path
        add_decorator_to_file(file_path, is_command=True)

    # 处理 User Queries
    print("\n👤 处理 User Queries:")
    for file_rel_path in USER_QUERIES:
        file_path = base_dir / file_rel_path
        add_decorator_to_file(file_path, is_command=False)

    print("\n✅ 批量处理完成！")


if __name__ == "__main__":
    main()
