"""Catalog module commands."""

from contexts.catalog.application.commands.create_category import (
    CreateCategoryCommand,
    CreateCategoryHandler,
)
from contexts.catalog.application.commands.create_product import (
    CreateProductCommand,
    CreateProductHandler,
)
from contexts.catalog.application.commands.delete_category import (
    DeleteCategoryCommand,
    DeleteCategoryHandler,
)
from contexts.catalog.application.commands.delete_product import (
    DeleteProductCommand,
    DeleteProductHandler,
)
from contexts.catalog.application.commands.update_category import (
    UpdateCategoryCommand,
    UpdateCategoryHandler,
)
from contexts.catalog.application.commands.update_product import (
    UpdateProductCommand,
    UpdateProductHandler,
)

__all__ = [
    # Product commands
    "CreateProductCommand",
    "CreateProductHandler",
    "UpdateProductCommand",
    "UpdateProductHandler",
    "DeleteProductCommand",
    "DeleteProductHandler",
    # Category commands
    "CreateCategoryCommand",
    "CreateCategoryHandler",
    "UpdateCategoryCommand",
    "UpdateCategoryHandler",
    "DeleteCategoryCommand",
    "DeleteCategoryHandler",
]
