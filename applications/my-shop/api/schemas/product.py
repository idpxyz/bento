"""Product API Schemas (DTOs)"""

from pydantic import BaseModel, Field


class ProductBase(BaseModel):
    """Base product schema"""

    name: str = Field(..., min_length=1, max_length=200, description="Product name")
    description: str | None = Field(None, max_length=1000, description="Product description")
    price: float = Field(..., gt=0, description="Product price (must be positive)")
    stock: int = Field(0, ge=0, description="Stock quantity")
    category_id: str | None = Field(None, description="Category ID")


class ProductCreate(ProductBase):
    """Schema for creating a product"""

    pass


class ProductUpdate(BaseModel):
    """Schema for updating a product"""

    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=1000)
    price: float | None = Field(None, gt=0)
    stock: int | None = Field(None, ge=0)
    category_id: str | None = None


class ProductResponse(ProductBase):
    """Schema for product response"""

    id: str = Field(..., description="Product ID")

    model_config = {"from_attributes": True}


class ProductList(BaseModel):
    """Schema for product list response"""

    items: list[ProductResponse]
    total: int
    page: int
    page_size: int
