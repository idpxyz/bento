"""Category API Response Models."""

from pydantic import BaseModel, Field


class CategoryResponse(BaseModel):
    """Category response model for API."""

    id: str = Field(..., description="Category ID")
    name: str = Field(..., description="Category name")
    description: str = Field(..., description="Category description")
    parent_id: str | None = Field(None, description="Parent category ID")
    is_root: bool = Field(..., description="Is root category")


class ListCategoriesResponse(BaseModel):
    """List categories response model for API."""

    items: list[CategoryResponse] = Field(..., description="List of categories")
    total: int = Field(..., ge=0, description="Total number of categories")
