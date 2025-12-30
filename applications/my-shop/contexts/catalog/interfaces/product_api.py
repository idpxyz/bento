"""Product API routes (FastAPI) - Thin Interface Layer - Complete Version"""

from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel

from contexts.catalog.application.commands import (
    CreateProductCommand,
    CreateProductHandler,
    DeleteProductCommand,
    DeleteProductHandler,
    UpdateProductCommand,
    UpdateProductHandler,
)
from contexts.catalog.application.queries import (
    GetProductHandler,
    GetProductQuery,
    ListProductsHandler,
    ListProductsQuery,
)
from contexts.catalog.interfaces.presenters import product_to_dict
from shared.infrastructure.dependencies import handler_dependency

router = APIRouter()


# ==================== Request/Response Models ====================


class CreateProductRequest(BaseModel):
    """Create product request model.

    Note: For idempotency, pass X-Idempotency-Key in HTTP Header.
    """

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
    stock: int | None = None
    sku: str | None = None
    brand: str | None = None
    is_active: bool | None = None


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


# ==================== API Routes ====================
#
# Note: All Handlers use handler_dependency() for clean OpenAPI schemas.
# No need for individual DI functions - universal factory pattern!
#


@router.post(
    "/",
    response_model=ProductResponse,
    status_code=201,
    summary="Create a new product",
)
async def create_product(
    request: CreateProductRequest,
    handler: CreateProductHandler = handler_dependency(CreateProductHandler),
) -> ProductResponse:
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

    product = await handler.execute(command)
    return ProductResponse(**product_to_dict(product))


@router.get(
    "/",
    response_model=ListProductsResponse,
    summary="List products",
)
async def list_products(
    handler: ListProductsHandler = handler_dependency(ListProductsHandler),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    category_id: str | None = Query(None),
) -> ListProductsResponse:
    """List products with pagination."""
    query = ListProductsQuery(
        page=page,
        page_size=page_size,
        category_id=category_id,
    )

    result = await handler.execute(query)

    return ListProductsResponse(
        items=[ProductResponse(**p.model_dump()) for p in result.products],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Get a product",
)
async def get_product(
    product_id: str,
    handler: GetProductHandler = handler_dependency(GetProductHandler),
) -> dict[str, Any]:
    """Get a product by ID."""
    from bento.core.exceptions import ApplicationException
    from fastapi import HTTPException

    try:
        query = GetProductQuery(product_id=product_id)
        product = await handler.execute(query)  # 返回 ProductDTO
        return product.model_dump()  # ✅ 使用 DTO 内置序列化
    except ApplicationException as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Product not found") from e
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.put(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Update a product",
)
async def update_product(
    product_id: str,
    request: UpdateProductRequest,
    handler: UpdateProductHandler = handler_dependency(UpdateProductHandler),
) -> dict[str, Any]:
    """Update a product."""
    command = UpdateProductCommand(
        product_id=product_id,
        name=request.name,
        description=request.description,
        price=request.price,
        stock=request.stock,
        sku=request.sku,
        brand=request.brand,
        is_active=request.is_active,
    )

    product = await handler.execute(command)
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
    handler: DeleteProductHandler = handler_dependency(DeleteProductHandler),
) -> None:
    """Delete a product (soft delete)."""
    from bento.core.exceptions import ApplicationException
    from fastapi import HTTPException

    try:
        command = DeleteProductCommand(product_id=product_id)
        await handler.execute(command)
    except ApplicationException as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Product not found") from None
        raise HTTPException(status_code=400, detail=str(e)) from None
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error") from None
