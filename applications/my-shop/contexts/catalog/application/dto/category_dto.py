"""Category DTO - Data Transfer Object for Category queries."""

from bento.application.dto import BaseDTO
from pydantic import Field


class CategoryDTO(BaseDTO):
    """Category Data Transfer Object.

    用于查询操作的数据传输对象，基于 Pydantic 提供高性能序列化和验证。

    注意：转换逻辑已迁移到 CategoryDTOMapper，符合 SOLID 原则中的单一职责原则。
    """

    id: str = Field(..., description="Category ID")
    name: str = Field(..., min_length=1, description="Category name")
    description: str = Field(..., description="Category description")
    parent_id: str | None = Field(None, description="Parent category ID")
    is_root: bool = Field(..., description="Is root category")
