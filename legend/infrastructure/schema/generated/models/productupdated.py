"""
从 product_updated.avsc 自动生成的 Pydantic 模型
"""

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Dict
from typing import List
from typing import Optional, Any


class ProductUpdated(BaseModel):
    """
    产品更新事件
    """
    product_id: str  # 产品ID
    name: str  # 产品名称
    description: Optional[str] = None  # 产品描述
    price: float  # 价格
    currency: str  # 货币
    categories: List[str]  # 分类
    attributes: Dict[str, str]  # 属性
    in_stock: bool  # 是否有库存
    updated_at: int  # 更新时间

    class Config:
        """模型配置"""
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

