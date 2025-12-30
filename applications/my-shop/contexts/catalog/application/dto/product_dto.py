"""Product DTO - Data Transfer Object for Product queries."""

from bento.application.dto import BaseDTO
from pydantic import Field


class ProductDTO(BaseDTO):
    """Product Data Transfer Object.

    用于查询操作的数据传输对象，基于 Pydantic 提供高性能序列化和验证。

    注意：转换逻辑已迁移到 ProductDTOMapper，符合 SOLID 原则中的单一职责原则。
    """

    id: str = Field(..., description="Product ID")
    name: str = Field(..., min_length=1, description="Product name")
    description: str = Field(..., description="Product description")
    price: float = Field(..., gt=0, description="Product price")
    stock: int = Field(..., ge=0, description="Stock quantity")
    sku: str | None = Field(None, description="SKU code")
    brand: str | None = Field(None, description="Brand name")
    is_active: bool = Field(True, description="Is product active")
    sales_count: int = Field(0, description="Sales count")
    category_id: str | None = Field(None, description="Category ID")
    is_categorized: bool = Field(False, description="Has category")

    # ✅ 新增计算字段 - 提供业务价值信息（可选，防止验证错误）
    price_tier: str | None = Field(None, description="Price tier: expensive or affordable")
    stock_status: str | None = Field(None, description="Stock status: in_stock or out_of_stock")
    formatted_price: str | None = Field(None, description="Formatted price with currency")
    availability: str | None = Field(None, description="Overall availability status")
