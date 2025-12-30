"""Product API Response Models."""

from pydantic import BaseModel, Field


class ProductResponse(BaseModel):
    """Product response model for API."""

    id: str = Field(..., description="Product ID")
    name: str = Field(..., description="Product name")
    description: str = Field(..., description="Product description")
    price: float = Field(..., gt=0, description="Product price")
    stock: int = Field(..., ge=0, description="Stock quantity")
    sku: str = Field(..., description="Product SKU")
    brand: str = Field(..., description="Product brand")
    is_active: bool = Field(..., description="Is product active")
    sales_count: int = Field(..., ge=0, description="Sales count")
    category_id: str | None = Field(None, description="Category ID")
    is_categorized: bool = Field(..., description="Is categorized")


class ListProductsResponse(BaseModel):
    """List products response model for API."""

    items: list[ProductResponse] = Field(..., description="List of products")
    total: int = Field(..., ge=0, description="Total number of products")
    page: int = Field(..., ge=1, description="Current page")
    page_size: int = Field(..., ge=1, description="Page size")
