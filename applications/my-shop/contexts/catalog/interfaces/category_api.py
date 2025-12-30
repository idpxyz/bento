"""Category API routes (FastAPI) - Thin Interface Layer"""

from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from contexts.catalog.application.commands import (
    CreateCategoryCommand,
    CreateCategoryHandler,
    DeleteCategoryCommand,
    DeleteCategoryHandler,
    UpdateCategoryCommand,
    UpdateCategoryHandler,
)
from contexts.catalog.application.queries import (
    GetCategoryHandler,
    GetCategoryQuery,
    GetCategoryTreeHandler,
    GetCategoryTreeQuery,
    ListCategoriesHandler,
    ListCategoriesQuery,
)
from contexts.catalog.application.queries.get_category_tree import CategoryTreeNodeDTO
from contexts.catalog.interfaces.category_presenters import category_to_dict
from shared.infrastructure.dependencies import handler_dependency

router = APIRouter()


# ==================== Request/Response Models ====================


class CreateCategoryRequest(BaseModel):
    """Create category request model."""

    name: str = Field(..., min_length=1, max_length=100, description="Category name")
    description: str = Field(..., min_length=1, max_length=500, description="Category description")
    parent_id: str | None = Field(None, description="Parent category ID (UUID format)")


class UpdateCategoryRequest(BaseModel):
    """Update category request model."""

    name: str | None = None
    description: str | None = None
    parent_id: str | None = None


class CategoryResponse(BaseModel):
    """Category response model."""

    id: str
    name: str
    description: str
    parent_id: str | None
    is_root: bool


class ListCategoriesResponse(BaseModel):
    """List categories response model."""

    items: list[CategoryResponse]
    total: int


# ==================== API Routes ====================
#
# Note: All Handlers use handler_dependency() for clean OpenAPI schemas.
# No need for individual DI functions - universal factory pattern!
#


@router.post(
    "/",
    response_model=CategoryResponse,
    status_code=201,
    summary="Create a new category",
)
async def create_category(
    request: CreateCategoryRequest,
    handler: CreateCategoryHandler = handler_dependency(CreateCategoryHandler),
) -> CategoryResponse:
    """Create a new category."""
    command = CreateCategoryCommand(
        name=request.name,
        description=request.description,
        parent_id=request.parent_id,
    )

    category = await handler.execute(command)
    return CategoryResponse(**category_to_dict(category))


@router.get(
    "/",
    response_model=ListCategoriesResponse,
    summary="List categories",
)
async def list_categories(
    handler: ListCategoriesHandler = handler_dependency(ListCategoriesHandler),
    parent_id: str | None = Query(None, description="Filter by parent category"),
) -> ListCategoriesResponse:
    """List categories with optional parent filter."""
    query = ListCategoriesQuery(parent_id=parent_id)

    result = await handler.execute(query)

    return ListCategoriesResponse(
        items=[CategoryResponse(**c.model_dump()) for c in result.categories],
        total=result.total,
    )


@router.get(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="Get a category",
)
async def get_category(
    category_id: str,
    handler: GetCategoryHandler = handler_dependency(GetCategoryHandler),
) -> CategoryResponse:
    """Get a category by ID."""
    query = GetCategoryQuery(category_id=category_id)
    category = await handler.execute(query)  # 返回 CategoryDTO
    return CategoryResponse(**category.model_dump())  # ✅ 使用 DTO 内置序列化


@router.put(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="Update a category",
)
async def update_category(
    category_id: str,
    request: UpdateCategoryRequest,
    handler: UpdateCategoryHandler = handler_dependency(UpdateCategoryHandler),
) -> CategoryResponse:
    """Update a category."""
    command = UpdateCategoryCommand(
        category_id=category_id,
        name=request.name,
        description=request.description,
        parent_id=request.parent_id,
    )

    category = await handler.execute(command)
    return CategoryResponse(**category_to_dict(category))


@router.delete(
    "/{category_id}",
    status_code=204,
    summary="Delete a category",
)
async def delete_category(
    category_id: str,
    handler: DeleteCategoryHandler = handler_dependency(DeleteCategoryHandler),
) -> None:
    """Delete a category (soft delete)."""
    command = DeleteCategoryCommand(category_id=category_id)
    await handler.execute(command)


@router.get(
    "/tree/all",
    response_model=list[CategoryTreeNodeDTO],
    summary="Get category tree structure",
)
async def get_category_tree(
    handler: GetCategoryTreeHandler = handler_dependency(GetCategoryTreeHandler),
) -> list[CategoryTreeNodeDTO]:
    """Get all categories in tree structure.

    Returns a hierarchical tree of all root categories with their children.
    """
    query = GetCategoryTreeQuery(root_id=None)
    return await handler.execute(query)


@router.get(
    "/tree/{root_id}",
    response_model=list[CategoryTreeNodeDTO],
    summary="Get category subtree",
)
async def get_category_subtree(
    root_id: str,
    handler: GetCategoryTreeHandler = handler_dependency(GetCategoryTreeHandler),
) -> list[CategoryTreeNodeDTO]:
    """Get a specific category and its subtree.

    Returns the specified category with all its descendants in tree structure.
    """
    query = GetCategoryTreeQuery(root_id=root_id)
    return await handler.execute(query)
