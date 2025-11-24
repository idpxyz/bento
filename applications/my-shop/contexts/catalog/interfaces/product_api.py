"""Product API routes (FastAPI) - Thin Interface Layer - Complete Version"""

from typing import Annotated, Any

from bento.persistence.uow import SQLAlchemyUnitOfWork
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from contexts.catalog.application.commands import (
    CreateProductCommand,
    CreateProductUseCase,
    DeleteProductCommand,
    DeleteProductUseCase,
    UpdateProductCommand,
    UpdateProductUseCase,
)
from contexts.catalog.application.queries import (
    GetProductQuery,
    GetProductUseCase,
    ListProductsQuery,
    ListProductsUseCase,
)
from contexts.catalog.interfaces.presenters import product_to_dict
from shared.infrastructure.dependencies import get_uow

router = APIRouter()


# ==================== Request/Response Models ====================


class CreateProductRequest(BaseModel):
    """Create product request model."""

    name: str
    description: str
    price: float
    stock: int = 0
    sku: str | None = None
    brand: str | None = None
    is_active: bool = True
    category_id: str | None = None  # 可选的分类ID


class UpdateProductRequest(BaseModel):
    """Update product request model."""

    name: str | None = None
    description: str | None = None
    price: float | None = None


class ProductResponse(BaseModel):
    """Product response model."""

    id: str
    name: str
    description: str
    price: float
    stock: int
    sku: str | None = None
    brand: str | None = None
    is_active: bool
    sales_count: int
    category_id: str | None = None
    is_categorized: bool


class ListProductsResponse(BaseModel):
    """List products response model."""

    items: list[ProductResponse]
    total: int
    page: int
    page_size: int


# ==================== Dependency Injection ====================


async def get_create_product_use_case(
    uow: SQLAlchemyUnitOfWork = Depends(get_uow),
) -> CreateProductUseCase:
    """Get create product use case (dependency)."""
    return CreateProductUseCase(uow)


async def get_list_products_use_case(
    uow: SQLAlchemyUnitOfWork = Depends(get_uow),
) -> ListProductsUseCase:
    """get_list_products_use_case (dependency)."""
    return ListProductsUseCase(uow)


async def get_get_product_use_case(
    uow: SQLAlchemyUnitOfWork = Depends(get_uow),
) -> GetProductUseCase:
    """get_get_product_use_case (dependency)."""
    return GetProductUseCase(uow)


async def get_update_product_use_case(
    uow: SQLAlchemyUnitOfWork = Depends(get_uow),
) -> UpdateProductUseCase:
    """get_update_product_use_case (dependency)."""
    return UpdateProductUseCase(uow)


async def get_delete_product_use_case(
    uow: SQLAlchemyUnitOfWork = Depends(get_uow),
) -> DeleteProductUseCase:
    """get_delete_product_use_case (dependency)."""
    return DeleteProductUseCase(uow)


# ==================== API Routes ====================


@router.post(
    "/",
    response_model=ProductResponse,
    status_code=201,
    summary="Create a new product",
)
async def create_product(
    request: CreateProductRequest,
    use_case: Annotated[CreateProductUseCase, Depends(get_create_product_use_case)],
) -> dict[str, Any]:
    """Create a new product."""
    command = CreateProductCommand(
        name=request.name,
        description=request.description,
        price=request.price,
        stock=request.stock,
        sku=request.sku,
        brand=request.brand,
        is_active=request.is_active,
        category_id=request.category_id,
    )

    product = await use_case.execute(command)
    return product_to_dict(product)


@router.get(
    "/",
    response_model=ListProductsResponse,
    summary="List products",
)
async def list_products(
    use_case: Annotated[ListProductsUseCase, Depends(get_list_products_use_case)],
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    category_id: str | None = Query(None),
) -> dict[str, Any]:
    """List products with pagination."""
    query = ListProductsQuery(
        page=page,
        page_size=page_size,
        category_id=category_id,
    )

    result = await use_case.execute(query)

    return {
        "items": [product_to_dict(p) for p in result.products],
        "total": result.total,
        "page": result.page,
        "page_size": result.page_size,
    }


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Get a product",
)
async def get_product(
    product_id: str,
    use_case: Annotated[GetProductUseCase, Depends(get_get_product_use_case)],
) -> dict[str, Any]:
    """Get a product by ID."""
    query = GetProductQuery(product_id=product_id)
    product = await use_case.execute(query)
    return product_to_dict(product)


@router.put(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Update a product",
)
async def update_product(
    product_id: str,
    request: UpdateProductRequest,
    use_case: Annotated[UpdateProductUseCase, Depends(get_update_product_use_case)],
) -> dict[str, Any]:
    """Update a product."""
    command = UpdateProductCommand(
        product_id=product_id,
        name=request.name,
        description=request.description,
        price=request.price,
    )

    product = await use_case.execute(command)
    return product_to_dict(product)


@router.get(
    "/ping",
    summary="Ping endpoint",
    status_code=200,
)
async def ping() -> dict[str, str]:
    """Ping endpoint for health check."""
    return {"status": "ok", "message": "pong"}


@router.delete(
    "/{product_id}",
    status_code=204,
    summary="Delete a product",
)
async def delete_product(
    product_id: str,
    use_case: Annotated[DeleteProductUseCase, Depends(get_delete_product_use_case)],
) -> None:
    """Delete a product (soft delete)."""
    command = DeleteProductCommand(product_id=product_id)
    await use_case.execute(command)
