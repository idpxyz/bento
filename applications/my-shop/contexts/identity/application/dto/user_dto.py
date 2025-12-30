"""User DTO - Data Transfer Object for User queries."""

from bento.application.dto import BaseDTO
from pydantic import Field


class UserDTO(BaseDTO):
    """User Data Transfer Object.

    用于查询操作的数据传输对象，基于 Pydantic 提供高性能序列化和验证。
    """

    id: str = Field(..., description="User ID")
    name: str = Field(..., min_length=1, description="User name")
    email: str = Field(..., description="User email address")
