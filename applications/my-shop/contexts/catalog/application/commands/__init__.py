"""Catalog module commands."""

from contexts.catalog.application.commands.create_category import (
    CreateCategoryCommand,
    CreateCategoryUseCase,
)
from contexts.catalog.application.commands.create_product import (
    CreateProductCommand,
    CreateProductUseCase,
)
from contexts.catalog.application.commands.delete_category import (
    DeleteCategoryCommand,
    DeleteCategoryUseCase,
)
from contexts.catalog.application.commands.delete_product import (
    DeleteProductCommand,
    DeleteProductUseCase,
)
from contexts.catalog.application.commands.update_category import (
    UpdateCategoryCommand,
    UpdateCategoryUseCase,
)
from contexts.catalog.application.commands.update_product import (
    UpdateProductCommand,
    UpdateProductUseCase,
)

__all__ = [
    # Product commands
    "CreateProductCommand",
    "CreateProductUseCase",
    "UpdateProductCommand",
    "UpdateProductUseCase",
    "DeleteProductCommand",
    "DeleteProductUseCase",
    # Category commands
    "CreateCategoryCommand",
    "CreateCategoryUseCase",
    "UpdateCategoryCommand",
    "UpdateCategoryUseCase",
    "DeleteCategoryCommand",
    "DeleteCategoryUseCase",
]
