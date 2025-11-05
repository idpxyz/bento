"""

从 product_added.proto 自动生成的 Pydantic 模型

"""



from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Dict, Optional



class ProductStatus(str, Enum):
    """枚举类型"""
    DRAFT = "draft"  # 草稿
    ACTIVE = "active"  # 已上架
    INACTIVE = "inactive"  # 已下架
    DELETED = "deleted"  # 已删除



class ProductImage(BaseModel):
    """
    ProductImage 模型
    """
    url: Optional[str] = None  # 图片URL
    alt: Optional[str] = None  # 替代文本
    is_primary: Optional[bool] = None  # 是否主图

    model_config = {
        "json_schema_extra": {"description": "ProductImage 模型"},
        "json_encoders": {datetime: lambda dt: dt.isoformat()}
    }

class ProductAdded(BaseModel):
    """
    ProductAdded 事件模型
    """
    product_id: Optional[str] = None  # 产品ID
    name: Optional[str] = None  # 产品名称
    description: Optional[str] = None  # 产品描述
    price: Optional[float] = None  # 价格
    categories: Optional[List[str]] = None  # 产品分类
    images: Optional[List[ProductImage]] = None  # 产品图片
    status: Optional[ProductStatus] = None  # 产品状态
    created_at: Optional[datetime] = None  # 创建时间
    created_by: Optional[str] = None  # 创建人ID

    model_config = {
        "json_schema_extra": {"description": "ProductAdded 事件模型"},
        "json_encoders": {datetime: lambda dt: dt.isoformat()}
    }