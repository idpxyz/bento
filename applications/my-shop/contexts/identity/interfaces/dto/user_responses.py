"""User API Response Models."""

from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    """User response model for API."""

    id: str = Field(..., description="User ID")
    name: str = Field(..., description="User name")
    email: str = Field(..., description="User email")


class ListUsersResponse(BaseModel):
    """List users response model for API."""

    items: list[UserResponse] = Field(..., description="List of users")
    total: int = Field(..., ge=0, description="Total number of users")
    page: int = Field(..., ge=1, description="Current page")
    page_size: int = Field(..., ge=1, description="Page size")
