"""User API Schemas (DTOs)"""

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Base user schema"""

    name: str = Field(..., min_length=1, max_length=100, description="User name")
    email: EmailStr = Field(..., description="User email address")


class UserCreate(UserBase):
    """Schema for creating a user"""

    pass


class UserUpdate(BaseModel):
    """Schema for updating a user"""

    name: str | None = Field(None, min_length=1, max_length=100)
    email: EmailStr | None = None


class UserResponse(UserBase):
    """Schema for user response"""

    id: str = Field(..., description="User ID")

    model_config = {"from_attributes": True}


class UserList(BaseModel):
    """Schema for user list response"""

    items: list[UserResponse]
    total: int
    page: int
    page_size: int
