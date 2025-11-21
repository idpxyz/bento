"""IPaymentService - Secondary Port（被驱动端口）

支付服务接口，定义 Ordering Context 处理支付的契约。
符合六边形架构原则：Domain 层定义接口，Infrastructure 层实现。

Port vs Adapter:
- Port（本文件）: Domain 层定义的接口契约
- Adapter（infrastructure/adapters/）: 接口的具体技术实现
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class PaymentMethod(str, Enum):
    """支付方式枚举"""

    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    ALIPAY = "alipay"
    WECHAT_PAY = "wechat_pay"
    PAYPAL = "paypal"


class PaymentStatus(str, Enum):
    """支付状态枚举"""

    PENDING = "pending"  # 待支付
    PROCESSING = "processing"  # 处理中
    SUCCESS = "success"  # 成功
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 已取消
    REFUNDED = "refunded"  # 已退款


@dataclass(frozen=True)
class PaymentRequest:
    """支付请求（值对象）"""

    order_id: str
    amount: float
    currency: str = "CNY"
    payment_method: PaymentMethod = PaymentMethod.ALIPAY
    description: str = ""


@dataclass(frozen=True)
class PaymentResult:
    """支付结果（值对象）"""

    transaction_id: str  # 交易ID
    status: PaymentStatus
    amount: float
    payment_method: PaymentMethod
    message: str = ""  # 结果消息
    paid_at: str | None = None  # 支付时间


class IPaymentService(ABC):
    """支付服务接口（Secondary Port - 被驱动端口）

    职责：
    1. 定义 Ordering BC 处理支付的契约
    2. 隔离支付网关的变化（反腐败层）
    3. 支持依赖倒置（Domain 不依赖具体支付实现）

    实现方式由 Adapter 决定：
    - AlipayAdapter: 支付宝支付（国内）
    - WeChatPayAdapter: 微信支付（国内）
    - StripeAdapter: Stripe 支付（国际）
    - MockPaymentAdapter: 模拟支付（测试）
    """

    @abstractmethod
    async def process_payment(self, request: PaymentRequest) -> PaymentResult:
        """处理支付

        Args:
            request: 支付请求

        Returns:
            PaymentResult: 支付结果

        Raises:
            PaymentException: 支付失败时抛出
        """
        pass

    @abstractmethod
    async def query_payment(self, transaction_id: str) -> PaymentResult:
        """查询支付状态

        Args:
            transaction_id: 交易ID

        Returns:
            PaymentResult: 支付结果
        """
        pass

    @abstractmethod
    async def cancel_payment(self, transaction_id: str) -> bool:
        """取消支付

        Args:
            transaction_id: 交易ID

        Returns:
            bool: 是否成功取消
        """
        pass

    @abstractmethod
    async def refund_payment(
        self, transaction_id: str, amount: float | None = None
    ) -> PaymentResult:
        """退款

        Args:
            transaction_id: 交易ID
            amount: 退款金额（None 表示全额退款）

        Returns:
            PaymentResult: 退款结果
        """
        pass
