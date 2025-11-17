"""Product API routes (FastAPI) - Thin Interface Layer"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from contexts.catalog.application.commands import (
    CreateProductCommand,
    CreateProductUseCase,
)
from contexts.catalog.application.queries import (
    ListProductsQuery,
    ListProductsUseCase,
)
from contexts.catalog.interfaces.presenters import product_to_dict

router = APIRouter()


# ==================== Request/Response Models ====================


class CreateProductRequest(BaseModel):
    """Create product request model."""

    name: str
    description: str
    price: float
    stock: int = 0
    category_id: str | None = None


class ProductResponse(BaseModel):
    """Product response model."""

    id: str
    name: str
    description: str
    price: float


class ListProductsResponse(BaseModel):
    """List products response model."""

    items: list[ProductResponse]
    total: int
    page: int
    page_size: int


# ==================== Dependency Injection ====================


async def get_create_product_use_case() -> CreateProductUseCase:
    """Get create product use case (dependency)."""
    from api.deps import get_unit_of_work

    uow = await get_unit_of_work()
    return CreateProductUseCase(uow)


async def get_list_products_use_case() -> ListProductsUseCase:
    """Get list products use case (dependency)."""
    from api.deps import get_unit_of_work

    uow = await get_unit_of_work()
    return ListProductsUseCase(uow)


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
    # 1. Request → Command
    command = CreateProductCommand(
        name=request.name,
        description=request.description,
        price=request.price,
        stock=request.stock,
        category_id=request.category_id,
    )

    # 2. Execute Use Case
    product = await use_case.execute(command)

    # 3. Domain → Response
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
    # 1. Request → Query
    query = ListProductsQuery(
        page=page,
        page_size=page_size,
        category_id=category_id,
    )

    # 2. Execute Use Case
    result = await use_case.execute(query)

    # 3. Domain → Response
    return {
        "items": [product_to_dict(p) for p in result.products],
        "total": result.total,
        "page": result.page,
        "page_size": result.page_size,
    }
