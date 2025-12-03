"""Category API routes (FastAPI) - Thin Interface Layer"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

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
    ListCategoriesHandler,
    ListCategoriesQuery,
)
from contexts.catalog.interfaces.category_presenters import category_to_dict
from shared.infrastructure.dependencies import get_handler

router = APIRouter()


# ==================== Request/Response Models ====================


class CreateCategoryRequest(BaseModel):
    """Create category request model."""

    name: str
    description: str
    parent_id: str | None = None


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
# Note: All Handlers are now injected using the universal get_handler() factory
# from shared.infrastructure.dependencies. No need for individual DI functions!
#


@router.post(
    "/",
    response_model=CategoryResponse,
    status_code=201,
    summary="Create a new category",
)
async def create_category(
    request: CreateCategoryRequest,
    handler: Annotated[CreateCategoryHandler, Depends(get_handler)],
) -> dict[str, Any]:
    """Create a new category."""
    command = CreateCategoryCommand(
        name=request.name,
        description=request.description,
        parent_id=request.parent_id,
    )

    category = await handler.execute(command)
    return category_to_dict(category)


@router.get(
    "/",
    response_model=ListCategoriesResponse,
    summary="List categories",
)
async def list_categories(
    handler: Annotated[ListCategoriesHandler, Depends(get_handler)],
    parent_id: str | None = Query(None, description="Filter by parent category"),
) -> dict[str, Any]:
    """List categories with optional parent filter."""
    query = ListCategoriesQuery(parent_id=parent_id)

    result = await handler.execute(query)

    return {
        "items": [category_to_dict(c) for c in result.categories],
        "total": result.total,
    }


@router.get(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="Get a category",
)
async def get_category(
    category_id: str,
    handler: Annotated[GetCategoryHandler, Depends(get_handler)],
) -> dict[str, Any]:
    """Get a category by ID."""
    query = GetCategoryQuery(category_id=category_id)
    category = await handler.execute(query)
    return category_to_dict(category)


@router.put(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="Update a category",
)
async def update_category(
    category_id: str,
    request: UpdateCategoryRequest,
    handler: Annotated[UpdateCategoryHandler, Depends(get_handler)],
) -> dict[str, Any]:
    """Update a category."""
    command = UpdateCategoryCommand(
        category_id=category_id,
        name=request.name,
        description=request.description,
        parent_id=request.parent_id,
    )

    category = await handler.execute(command)
    return category_to_dict(category)


@router.delete(
    "/{category_id}",
    status_code=204,
    summary="Delete a category",
)
async def delete_category(
    category_id: str,
    handler: Annotated[DeleteCategoryHandler, Depends(get_handler)],
) -> None:
    """Delete a category (soft delete)."""
    command = DeleteCategoryCommand(category_id=category_id)
    await handler.execute(command)
