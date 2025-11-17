"""Category API routes (FastAPI) - Thin Interface Layer"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from contexts.catalog.application.commands import (
    CreateCategoryCommand,
    CreateCategoryUseCase,
    DeleteCategoryCommand,
    DeleteCategoryUseCase,
    UpdateCategoryCommand,
    UpdateCategoryUseCase,
)
from contexts.catalog.application.queries import (
    GetCategoryQuery,
    GetCategoryUseCase,
    ListCategoriesQuery,
    ListCategoriesUseCase,
)
from contexts.catalog.interfaces.category_presenters import category_to_dict
from bento.persistence.uow import SQLAlchemyUnitOfWork

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


# ==================== Dependency Injection ====================


async def get_create_category_use_case() -> CreateCategoryUseCase:
    """Get create category use case (dependency)."""
    from shared.infrastructure.dependencies import get_unit_of_work, get_uow

    uow = await get_unit_of_work()
    return CreateCategoryUseCase(uow)


async def get_list_categories_use_case(
    uow: SQLAlchemyUnitOfWork = Depends(get_uow),
) -> ListCategoriesUseCase:
    """get_list_categories_use_case (dependency)."""
    return ListCategoriesUseCase(uow)


async def get_get_category_use_case(
    uow: SQLAlchemyUnitOfWork = Depends(get_uow),
) -> GetCategoryUseCase:
    """get_get_category_use_case (dependency)."""
    return GetCategoryUseCase(uow)


async def get_update_category_use_case(
    uow: SQLAlchemyUnitOfWork = Depends(get_uow),
) -> UpdateCategoryUseCase:
    """get_update_category_use_case (dependency)."""
    return UpdateCategoryUseCase(uow)


async def get_delete_category_use_case(
    uow: SQLAlchemyUnitOfWork = Depends(get_uow),
) -> DeleteCategoryUseCase:
    """get_delete_category_use_case (dependency)."""
    return DeleteCategoryUseCase(uow)


# ==================== API Routes ====================


@router.post(
    "/",
    response_model=CategoryResponse,
    status_code=201,
    summary="Create a new category",
)
async def create_category(
    request: CreateCategoryRequest,
    use_case: Annotated[CreateCategoryUseCase, Depends(get_create_category_use_case)],
) -> dict[str, Any]:
    """Create a new category."""
    command = CreateCategoryCommand(
        name=request.name,
        description=request.description,
        parent_id=request.parent_id,
    )

    category = await use_case.execute(command)
    return category_to_dict(category)


@router.get(
    "/",
    response_model=ListCategoriesResponse,
    summary="List categories",
)
async def list_categories(
    use_case: Annotated[ListCategoriesUseCase, Depends(get_list_categories_use_case)],
    parent_id: str | None = Query(None, description="Filter by parent category"),
) -> dict[str, Any]:
    """List categories with optional parent filter."""
    query = ListCategoriesQuery(parent_id=parent_id)

    result = await use_case.execute(query)

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
    use_case: Annotated[GetCategoryUseCase, Depends(get_get_category_use_case)],
) -> dict[str, Any]:
    """Get a category by ID."""
    query = GetCategoryQuery(category_id=category_id)
    category = await use_case.execute(query)
    return category_to_dict(category)


@router.put(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="Update a category",
)
async def update_category(
    category_id: str,
    request: UpdateCategoryRequest,
    use_case: Annotated[UpdateCategoryUseCase, Depends(get_update_category_use_case)],
) -> dict[str, Any]:
    """Update a category."""
    command = UpdateCategoryCommand(
        category_id=category_id,
        name=request.name,
        description=request.description,
        parent_id=request.parent_id,
    )

    category = await use_case.execute(command)
    return category_to_dict(category)


@router.delete(
    "/{category_id}",
    status_code=204,
    summary="Delete a category",
)
async def delete_category(
    category_id: str,
    use_case: Annotated[DeleteCategoryUseCase, Depends(get_delete_category_use_case)],
) -> None:
    """Delete a category (soft delete)."""
    command = DeleteCategoryCommand(category_id=category_id)
    await use_case.execute(command)
