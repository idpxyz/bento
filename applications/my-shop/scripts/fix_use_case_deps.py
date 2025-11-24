#!/usr/bin/env python3
"""Batch fix all use case dependency injection patterns."""

import re
from pathlib import Path

# Files to fix
API_FILES = [
    "contexts/catalog/interfaces/product_api.py",
    "contexts/catalog/interfaces/category_api.py",
    "contexts/identity/interfaces/user_api.py",
]


def fix_imports(content: str, filename: str) -> str:
    """Add required imports if missing."""
    has_uow_import = "from bento.persistence.uow import SQLAlchemyUnitOfWork" in content
    has_get_uow_import = (
        "from shared.infrastructure.dependencies import" in content and "get_uow" in content
    )

    if not has_uow_import or not has_get_uow_import:
        # Find the imports section
        lines = content.split("\n")
        insert_pos = 0

        # Find last import line
        for i, line in enumerate(lines):
            if line.startswith("from ") or line.startswith("import "):
                insert_pos = i + 1

        imports_to_add = []
        if not has_uow_import:
            imports_to_add.append("from bento.persistence.uow import SQLAlchemyUnitOfWork")
        if not has_get_uow_import:
            # Check if we need to add get_uow to existing import
            for i, line in enumerate(lines):
                if "from shared.infrastructure.dependencies import" in line:
                    if "get_uow" not in line:
                        # Add get_uow to the import
                        lines[i] = line.rstrip() + ", get_uow"
                    break
            else:
                imports_to_add.append("from shared.infrastructure.dependencies import get_uow")

        if imports_to_add:
            lines.insert(insert_pos, "\n".join(imports_to_add))
            content = "\n".join(lines)

    return content


def fix_use_case_function(content: str) -> str:
    """Fix use case dependency injection functions."""
    # Pattern for old style
    old_pattern = r'''async def (get_\w+_use_case)\(\) -> (\w+UseCase):
    """[^"]+"""
    from shared\.infrastructure\.dependencies import get_unit_of_work

    uow = await get_unit_of_work\(\)
    return \2\(uow\)'''

    # Replacement
    new_pattern = r'''async def \1(
    uow: SQLAlchemyUnitOfWork = Depends(get_uow),
) -> \2:
    """\1 (dependency)."""
    return \2(uow)'''

    content = re.sub(old_pattern, new_pattern, content)

    return content


def main():
    """Main function."""
    for file_path in API_FILES:
        path = Path(file_path)
        if not path.exists():
            print(f"⚠️  File not found: {file_path}")
            continue

        print(f"📝 Processing: {file_path}")
        content = path.read_text()

        # Fix imports
        content = fix_imports(content, file_path)

        # Fix use case functions
        original_content = content
        content = fix_use_case_function(content)

        if content != original_content:
            path.write_text(content)
            print(f"✅ Fixed: {file_path}")
        else:
            print(f"⏭️  No changes needed: {file_path}")


if __name__ == "__main__":
    main()
