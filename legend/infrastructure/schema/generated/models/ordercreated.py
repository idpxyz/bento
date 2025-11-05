"""

从 order_created.proto 自动生成的 Pydantic 模型

"""



from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Dict, Optional



class OrderItem(BaseModel):
    """
    OrderItem 模型
    """
    product_id: Optional[str] = None  # 产品ID
    product_name: Optional[str] = None  # 产品名称
    quantity: Optional[int] = None  # 数量
    unit_price: Optional[float] = None  # 单价
    subtotal: Optional[float] = None  # 小计

    model_config = {
        "json_schema_extra": {"description": "OrderItem 模型"},
        "json_encoders": {datetime: lambda dt: dt.isoformat()}
    }

class OrderCreated(BaseModel):
    """
    OrderCreated 事件模型
    """
    order_id: Optional[str] = None  # 订单ID
    customer_id: Optional[str] = None  # 客户ID
    items: Optional[List[OrderItem]] = None  # 订单项目
    total_amount: Optional[float] = None  # 总金额
    currency: Optional[str] = None  # 货币
    status: Optional[str] = None  # 订单状态
    created_at: Optional[datetime] = None  # 创建时间

    model_config = {
        "json_schema_extra": {"description": "OrderCreated 事件模型"},
        "json_encoders": {datetime: lambda dt: dt.isoformat()}
    }