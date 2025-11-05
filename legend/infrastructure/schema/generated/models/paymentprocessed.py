"""
从 payment_processed.json 自动生成的 Pydantic 模型
"""

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Dict, Any
from typing import Dict, List, Any, Optional
from typing import Literal
from typing import Optional


class PaymentMethod(BaseModel):
    """
    支付方式详情
    """
    type: Literal['CREDIT_CARD', 'DEBIT_CARD', 'ALIPAY', 'WECHAT', 'BANK_TRANSFER']  # 支付方式类型
    last4: Optional[str] = None  # 卡号末四位（如适用）
    expiry_date: Optional[str] = None  # 过期日期（如适用）

    class Config:
        """模型配置"""
        json_schema_extra = {
            'description': '支付方式详情'
        }

class PaymentProcessed(BaseModel):
    """
    支付处理完成事件
    """
    payment_id: str  # 支付ID
    order_id: str  # 关联的订单ID
    transaction_id: Optional[str] = None  # 支付网关交易ID
    amount: float  # 支付金额
    currency: Optional[str] = 'CNY'  # 货币类型
    status: Literal['SUCCEEDED', 'FAILED', 'PENDING', 'REFUNDED']  # 支付状态
    payment_method: PaymentMethod  # 支付方式详情
    processed_at: datetime  # 处理时间
    error_code: Optional[str] = None  # 错误代码（如果支付失败）
    error_message: Optional[str] = None  # 错误消息（如果支付失败）
    metadata: Dict[str, Any] = None  # 元数据

    class Config:
        """模型配置"""
        json_schema_extra = {
            'description': '元数据'
        }
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }
